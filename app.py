import random
from dotenv import load_dotenv
import chainlit as cl
import openai
from movie_functions import *


load_dotenv()

# Note: If switching to LangSmith, uncomment the following, and replace @observe with @traceable
from langsmith.wrappers import wrap_openai
from langsmith import traceable
client = wrap_openai(openai.AsyncClient())


gen_kwargs = {
    "model": "gpt-4o-mini",
    "temperature": 0.2,
    "max_tokens": 500
}

function_keywords = [
    'get_now_playing_movies(',
    'get_showtimes(',
    'buy_ticket(',
    'get_reviews(',
    'pick_random_movie(',
]

SYSTEM_PROMPT = """\
You are a helpful assistant that can answer questions about movies playing in theaters.
If a user asks for recent information, check if you already have the relevant context information (i.e. now playing movies or showtimes for movies).
If you do, then output the contextual information.
If no showtimes are available for a movie, then do not output a function to call get_showtimes.
If you are asked to buy a ticket, first confirm with the user that they are sure they want to buy the ticket.
Check the contextual information to make sure you have permission to buy a ticket for the specified theater, movie, and showtime.
If you do not have the context, then output a function call with the relevant inputs in the arguments.
if you need to get more information from the user **without** calling a function ask the user for the information.
If you need to fetch more information using a function, then pick the relevant function and output "sure, let me check that for you" before outputting the function call.
Call functions using Python syntax in plain text, no code blocks.

You have access to the following functions:
- get_now_playing_movies()
- get_showtimes(title, location)
- buy_ticket(theater, movie, showtime)
- get_reviews(movie_id)
- pick_random_movie(movies)

When outputting the function for get_showtimes, do not include the variable names.
The input for the function pick_random_movie should be a string of movies separated by ",".
"""

@traceable
@cl.on_chat_start
def on_chat_start():    
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)

@traceable
async def generate_response(client, message_history, gen_kwargs):
    full_response = ""
    stream = await client.chat.completions.create(messages=message_history, stream=True, **gen_kwargs)
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            full_response += token
    print("full response generated")
    print(full_response)
    # await response_message.send()
    if any(keyword in full_response for keyword in function_keywords): 
        print("sure, let me check that for you")
        await cl.Message(content="Sure, let me check that for you...").send()
    else:
        #remove the "sure, let me check that for you" message from the full_response
        full_response = full_response.replace("Sure, let me check that for you.", "")
    
    response_message = cl.Message(content=full_response)
    return response_message

@cl.on_message
@traceable
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})
    
    response_message = await generate_response(client, message_history, gen_kwargs)
    print("initial response generated:")
    print(response_message.content)
    print("checking for function keywords")
    while any(keyword in response_message.content for keyword in function_keywords):
        for keyword in function_keywords:
            if keyword in response_message.content:
                match keyword:
                      case 'get_now_playing_movies(':
                          # Handle get_now_playing_movies
                          print("running get_now_playing_movies()")
                          additional_context = get_now_playing_movies()
                          message_history.append({"role": "system", "content": f"Fetched Context: {additional_context}"})
                          pass
                      case 'get_showtimes(':
                          # Handle get_showtimes
                          print("running get_showtimes()")

                          # Extract title and location from the response_message.content
                          content = response_message.content
                          title_start = content.find('get_showtimes(') + len('get_showtimes(')
                          title_end = content.find(',', title_start)
                          location_end = content.find(')', title_end)
                          
                          if title_start != -1 and title_end != -1 and location_end != -1:
                              title = content[title_start:title_end].strip()
                              location = content[title_end+1:location_end].strip()
                              additional_context = get_showtimes(title, location)
                          else:
                              additional_context = "Error: Unable to extract title and location from the message."
                          message_history.append({"role": "system", "content": f"Fetched Context: {additional_context}"})
                          pass
                      case 'buy_ticket(':
                          # Handle buy_ticket
                          print("running buy_ticket()")
                          # Extract theater, movie, and showtime from the response_message.content
                          content = response_message.content
                          theater_start = content.find('buy_ticket(') + len('buy_ticket(')
                          theater_end = content.find(',', theater_start)
                          movie_start = theater_end + 1
                          movie_end = content.find(',', movie_start)
                          showtime_start = movie_end + 1
                          showtime_end = content.find(')', showtime_start)
                          
                          if theater_start != -1 and theater_end != -1 and movie_start != -1 and movie_end != -1 and showtime_start != -1 and showtime_end != -1:
                              theater = content[theater_start:theater_end].strip()
                              movie = content[movie_start:movie_end].strip()
                              showtime = content[showtime_start:showtime_end].strip()
                              additional_context = buy_ticket(theater, movie, showtime)
                          else:
                              additional_context = "Error: Unable to extract theater, movie, and showtime from the message."
                          
                          message_history.append({"role": "system", "content": f"Fetched Context: {additional_context}"})
                          pass
                      case 'get_reviews(':
                          # Handle get_reviews
                          print("running get_reviews()")

                          #TODO: need to add second system prompt to get the movie_id from searching the movie title
                          
                          # Extract movie_id from the response_message.content
                          content = response_message.content
                          movie_id_start = content.find('get_reviews(') + len('get_reviews(')
                          movie_id_end = content.find(')', movie_id_start)
                          
                          if movie_id_start != -1 and movie_id_end != -1:
                              movie_id = content[movie_id_start:movie_id_end].strip()
                              additional_context = get_reviews(movie_id)
                          else:
                              additional_context = "Error: Unable to extract movie_id from the message."
                          
                          message_history.append({"role": "system", "content": f"Fetched Context: {additional_context}"})
                          pass
                      case 'pick_random_movie(':
                          # Handle pick_random_movie
                          print("running pick_random_movie()")
                          # Extract movies from the response_message.content
                          function_call = response_message.content
                          start = function_call.find('(') + 1
                          end = function_call.find(')')

                          # Extract the arguments substring
                          arguments = function_call[start:end]
                          random_movie = random.choice(arguments.split(','))
                          print(f"random_movie:{random_movie}")
                          message_history.append({"role": "system", "content": f"Random movie picked is: {random_movie}"})
                          additional_context = random_movie
                          pass
                          break
        # at this point, we've processed the function call and added the context to the message history
        # we can now generate a new response
        response_message = await generate_response(client, message_history, gen_kwargs)
    # end of while loop 
    print("end of while loop")
    print(response_message.content)
    await response_message.send()

    # adds the response to the message history
    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)

if __name__ == "__main__":
    cl.main()
