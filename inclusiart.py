import streamlit as st
from openai import OpenAI
import random
import sqlite3
import requests
import pymongo
from pymongo import MongoClient
from google_drive_utils import upload_image_to_drive

# Initialize OpenAI client with API key
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# MongoDB Setup
@st.cache_resource
def get_mongo_connection():
    # Connect to MongoDB using credentials from secrets.toml
    client = MongoClient(st.secrets["mongo"]["uri"])
    db = client['inclusiai_db']  # Database name
    return db

db = get_mongo_connection()
user_data_collection = db['inclusive_data']  # Collection name

# SQLite Database Setup
# def setup_database():
#     conn = sqlite3.connect('inclusiai_data.db')
#     c = conn.cursor()
#     c.execute('''CREATE TABLE IF NOT EXISTS user_data
#                  (prolific_id TEXT PRIMARY KEY,
#                  user_prompt TEXT,
#                  bias_example TEXT,
#                  inclusive_suggestion TEXT,
#                  final_prompt TEXT,
#                  image_url TEXT,
#                  rating INTEGER,
#                  random_object TEXT,
#                  test_prompt TEXT,
#                  test_image_url TEXT,
#                  random_code INTEGER UNIQUE)''')
#     conn.commit()
#     conn.close()

# setup_database()

# Database Operations
# def insert_user_data(data):
#     conn = sqlite3.connect('inclusiai_data.db')
#     c = conn.cursor()
#     try:
#         c.execute('''INSERT INTO user_data VALUES
#                      (:prolific_id, :user_prompt, :bias_example, :inclusive_suggestion,
#                      :final_prompt, :image_url, :rating, :random_object, :test_prompt,
#                      :test_image_url, :random_code)''', data)
#         conn.commit()
#         return True
#     except sqlite3.IntegrityError:
#         return False
#     finally:
#         conn.close()

# def check_prolific_id_exists(prolific_id):
#     conn = sqlite3.connect('inclusiai_data.db')
#     c = conn.cursor()
#     c.execute("SELECT 1 FROM user_data WHERE prolific_id = ?", (prolific_id,))
#     exists = c.fetchone() is not None
#     conn.close()
#     return exists

# def check_random_code_exists(random_code):
#     conn = sqlite3.connect('inclusiai_data.db')
#     c = conn.cursor()
#     c.execute("SELECT 1 FROM user_data WHERE random_code = ?", (random_code,))
#     exists = c.fetchone() is not None
#     conn.close()
#     return exists

# def generate_unique_random_code():
#     while True:
#         random_code = random.randint(1000, 9999)
#         if not check_random_code_exists(random_code):
#             return random_code

def insert_user_data(data):
    try:
        user_data_collection.insert_one(data)
        return True
    except Exception as e:
        st.error(f"Error inserting data: {e}")
        return False

def check_prolific_id_exists(prolific_id):
    return user_data_collection.find_one({"prolific_id": prolific_id}) is not None

def check_random_code_exists(random_code):
    return user_data_collection.find_one({"random_code": random_code}) is not None

def generate_unique_random_code():
    while True:
        random_code = random.randint(1000, 9999)
        if not check_random_code_exists(random_code):
            return random_code


# Function to get bias example from OpenAI using ChatCompletion API
def get_bias_example(user_prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """You are an expert in identifying unconscious bias, stereotypes, and representation issues in character descriptions. Focus on detecting subtle biases related to:
- Gender roles and expectations
- Cultural and ethnic stereotypes
- Physical appearance assumptions
- Age-related prejudices
- Socioeconomic stereotypes
Provide specific, concrete examples of potential biases."""},
            {"role": "user", "content": f"Analyze this character description: '{user_prompt}'. In one clear, specific sentence, identify the most significant potential bias or stereotype that could emerge in the visual representation."}
        ],
        max_tokens=100,
        temperature=0.7
    )
    return response.choices[0].message.content

# Function to provide more inclusive alternatives for the user's prompt
def suggest_inclusive_prompt(user_prompt,bias_example):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """You are an expert in rewriting character descriptions to be more inclusive. Your task is to:
- Keep the exact same character concept
- Remove potentially biased language
Provide only the rewritten prompt without any explanation."""},
            {"role": "user", "content": f"Rewrite this character description to be more inclusive while keeping the same core concept: '{user_prompt}'. Address this specific bias: '{bias_example}'. Dont print text like 'Rewrite:' before the description"}
        ],
        max_tokens=100,
        temperature=0.7
    )
    return response.choices[0].message.content

# Function to get random object from OpenAI using ChatCompletion API
def get_random_object(user_prompt):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """Generate a single common profession from these categories:
- Service workers (waiter, cashier, receptionist)
- Office workers (accountant, secretary)
- Healthcare workers (nurse, doctor)
- Education (teacher, professor)
- Trade workers (plumber, electrician)
- Business professionals (manager, salesperson)
Provide only the profession name without any context or explanation."""},
            {"role": "user", "content": "Generate a single common profession that would require careful description."}
        ],
        max_tokens=100,
        temperature=0.7
    )
    return response.choices[0].message.content

# Function to generate an image using DALL·E 3 API and upload to Google Drive
def generate_image(final_prompt, prolific_id):
    response = client.images.generate(
        model="dall-e-3",
        prompt=final_prompt,
        size="1024x1024",
        quality="standard"
    )
    image_url = response.data[0].url
    
    # Download the image
    image_response = requests.get(image_url)
    image_bytes = image_response.content
    
    # Upload to Google Drive
    drive_link = upload_image_to_drive(image_bytes, f"{prolific_id}_prompted.jpg")
    print(drive_link)
    print(image_url)
    return (drive_link,image_url)

def generate_test_image(final_prompt, prolific_id):
    response = client.images.generate(
        model="dall-e-3",
        prompt=final_prompt,
        size="1024x1024",
        quality="standard"
    )
    image_url = response.data[0].url
    
    # Download the image
    image_response = requests.get(image_url)
    image_bytes = image_response.content
    
    # Upload to Google Drive
    drive_link = upload_image_to_drive(image_bytes, f"{prolific_id}_test.jpg")
    print(drive_link)
    return (drive_link,image_url)

# Initialize session state variables
if 'inclusive_suggestion' not in st.session_state:
    st.session_state['inclusive_suggestion'] = ""
if 'random_object' not in st.session_state:
    st.session_state['random_object'] = ""
if 'bias_example' not in st.session_state:
    st.session_state['bias_example'] = ""
if 'final_confirmed' not in st.session_state:
    st.session_state['final_confirmed'] = False
if 'image_url' not in st.session_state:
    st.session_state['image_url'] = None
if 'test_image_url' not in st.session_state:
    st.session_state['test_image_url'] = None
if 'display_prompt_image' not in st.session_state:
    st.session_state['display_prompt_image'] = None
if 'display_test_image' not in st.session_state:
    st.session_state['display_test_image'] = None
if 'feedback_given' not in st.session_state:
    st.session_state['feedback_given'] = False
if 'rating' not in st.session_state:
    st.session_state['rating'] = None
if 'additional_feedback_given' not in st.session_state:
    st.session_state['additional_feedback_given'] = False
if 'additional_rating' not in st.session_state:
    st.session_state['additional_rating'] = None
if 'random_code' not in st.session_state:
    st.session_state['random_code'] = None
if 'user_prompt_submitted' not in st.session_state:
    st.session_state['user_prompt_submitted'] = False
if 'additional_feedback_submitted' not in st.session_state:
    st.session_state['additional_feedback_submitted'] = False
if 'prolific_id_submitted' not in st.session_state:
    st.session_state['prolific_id_submitted'] = False
if 'test_prompt_submitted' not in st.session_state:
    st.session_state['test_prompt_submitted'] = False
if 'save_button_clicked' not in st.session_state:
    st.session_state['save_button_clicked'] = False
    

# Step 1: Introduce InclusiArt AI
st.title("InclusiArt AI")
st.write("""
Welcome to InclusiArt AI! I am a text-to-image generative AI tool designed to help you bring your fantasy characters to life. Simply describe your character, and I'll generate an image based on your description.
""")

# Step 2: Ask users for their Prolific ID
if not st.session_state['prolific_id_submitted']:
    prolific_id = str(st.text_input("What is your Prolific ID?", key="prolific_id_input"))
    if prolific_id:
        if check_prolific_id_exists(prolific_id):
            st.error("Error: This Prolific ID has already been used. Please contact the researcher if you believe this is a mistake.")
        else:
            st.session_state['prolific_id'] = prolific_id
            st.session_state['prolific_id_submitted'] = True
            st.rerun()
else:
    st.text_input("What is your Prolific ID?", value=st.session_state['prolific_id'], disabled=True)

if st.session_state['prolific_id_submitted']:
    # Step 3: Ask users what they would like to draw
    if not st.session_state['user_prompt_submitted']:
        user_prompt = st.text_input("What would you like to draw? Describe your fantasy character below:", key="initial_prompt_input")
        if user_prompt:
            st.session_state['user_prompt'] = user_prompt
            st.session_state['user_prompt_submitted'] = True
            st.rerun()
    else:
        st.text_input("What would you like to draw? Describe your fantasy character below:", value=st.session_state['user_prompt'], disabled=True)

    if st.session_state['user_prompt_submitted']:
        # Step 4: Inform users about potential bias
        st.write(f"You want to draw: {st.session_state['user_prompt']}")
        st.warning("""
        AI model may produce biased or stereotypical portrayals of characters due to the nature of its training data.
        """)

        # Step 5: Generate bias example and inclusive suggestion
        if not st.session_state['inclusive_suggestion']:
            with st.spinner('Analyzing your prompt for potential biases...'):
                st.session_state['bias_example'] = get_bias_example(st.session_state['user_prompt'])
            with st.spinner('Suggesting more inclusive alternatives...'):
                if st.session_state['bias_example']:
                    st.session_state['inclusive_suggestion'] = suggest_inclusive_prompt(st.session_state['user_prompt'],st.session_state['bias_example'])

        if st.session_state['bias_example']:
            st.write(f"Example of potential bias: {st.session_state['bias_example']}")

        # Step 6: Display suggested inclusive prompt
        st.write("Suggested Inclusive Prompt:")
        st.code(st.session_state['inclusive_suggestion'])

        # Step 7: Ask for final prompt before generating the image
        if not st.session_state['final_confirmed']:
            final_prompt = st.text_input("Please confirm or modify your final prompt before generating the image:", value="")
            if st.button("Confirm Final Prompt"):
                if final_prompt.strip() == "":
                    final_prompt = st.session_state['inclusive_suggestion']
                st.session_state['final_confirmed'] = True
                st.session_state['final_prompt'] = final_prompt
                st.rerun()

        if st.session_state['final_confirmed']:
            st.text_area("Final Prompt (Confirmed)", value=st.session_state['final_prompt'], height=100, disabled=True)

            # Generate image based on confirmed final prompt
            if not st.session_state['image_url']:
                with st.spinner('Generating your image...'):
                    image_url, display_prompt_image = generate_image(st.session_state['final_prompt'], st.session_state['prolific_id'])
                    if image_url:
                        st.session_state['image_url'] = image_url
                        st.session_state['display_prompt_image'] = display_prompt_image

            # Display generated image result
            if st.session_state['image_url']:
                try:
                    st.image(st.session_state['display_prompt_image'], caption=f"Generated Image based on: {st.session_state['final_prompt']}", use_container_width=True)
                except Exception as e:
                    st.error(f"Error displaying the image: {str(e)}")

            # Step 8: Ask for user feedback
            rating_options = [1, 2, 3, 4, 5, 6, 7]
            rating_disabled = st.session_state["feedback_given"]
            rating = st.radio(
                "How satisfied are you with the generated image? (1 being the lowest and 7 being the highest)",
                options=rating_options,
                index=None,
                disabled=rating_disabled,
                key="rating_radio"
            )

            if rating is not None and not rating_disabled:
                st.session_state["rating"] = rating
                st.session_state["feedback_given"] = True
                st.write(f"Thank you for your feedback! You rated your satisfaction as: {rating}/7")
                st.rerun()

            if st.session_state["feedback_given"]:
                # Step 9: Ask for additional feedback
                if not st.session_state['additional_feedback_submitted']:
                    additional_feedback = st.text_input("Any feedback about the inclusiveness of the AI-generated image?", key="additional_feedback_input")
                    if additional_feedback:
                        st.session_state['additional_feedback'] = additional_feedback
                        st.session_state['additional_feedback_submitted'] = True
                        st.rerun()
                else:
                    st.text_input("Any feedback about the inclusiveness of the AI-generated image?", value=st.session_state['additional_feedback'], disabled=True)

                if st.session_state['additional_feedback_submitted']:
                    # Step 10: Test user's understanding of inclusive prompting
                    if not st.session_state['random_object']:
                        st.session_state['random_object'] = get_random_object("")

                    st.write(f"Now, to test your understanding of inclusive prompting, write an inclusive prompt to generate an image of: **{st.session_state['random_object']}**")

                    if not st.session_state['test_prompt_submitted']:
                        test_prompt = st.text_input("Write your prompt here:", key="test_prompt_input")
                        if test_prompt:
                            st.session_state['test_prompt'] = test_prompt
                            st.session_state['test_prompt_submitted'] = True
                            st.rerun()
                    else:
                        st.text_input("Write your prompt here:", value=st.session_state['test_prompt'], disabled=True)

                    if st.session_state['test_prompt_submitted']:
                        # Generate image based on test prompt
                        if not st.session_state['test_image_url']:
                            with st.spinner('Generating your image...'):
                                test_image_url, display_test_image = generate_test_image(st.session_state['test_prompt'], st.session_state['prolific_id'])
                                if test_image_url:
                                    st.session_state['test_image_url'] = test_image_url
                                    st.session_state['display_test_image'] = display_test_image

                        # Display generated image result
                        if st.session_state['test_image_url']:
                            try:
                                st.image(st.session_state['display_test_image'], caption=f"Generated Image based on: {st.session_state['test_prompt']}", use_container_width=True)
                            except Exception as e:
                                st.error(f"Error displaying the image: {str(e)}")

                        # Step 11: Ask for user feedback
                        additional_rating_options = [1, 2, 3, 4, 5, 6, 7]
                        additional_rating_disabled = st.session_state["additional_feedback_given"]
                        additional_rating = st.radio(
                            "How satisfied are you with the generated image? (1 being the lowest and 7 being the highest)",
                            options=additional_rating_options,
                            index=None,
                            disabled=additional_rating_disabled,
                            key="additional_rating_radio"
                        )

                        if additional_rating is not None and not additional_rating_disabled:
                            st.session_state["additional_rating"] = additional_rating
                            st.session_state["additional_feedback_given"] = True
                            st.write(f"Thank you for your feedback! You rated your satisfaction as: {additional_rating}/7")
                            st.rerun()
                        

                        if st.session_state["additional_feedback_given"]:
                            # # Step 12: Provide random code to proceed
                            # if not st.session_state['random_code']:
                            #     st.session_state['random_code'] = generate_unique_random_code()

                            # st.write(f"Here is your code to proceed: **{st.session_state['random_code']}**")

                            # Step 13: Add "Save and Get Code" button
                            if not st.session_state['save_button_clicked']:
                                if st.button("Save and Receive Code"):
                                    # Gather all the data
                                    data = {
                                        'prolific_id': st.session_state.get('prolific_id', ''),
                                        'user_prompt': st.session_state.get('user_prompt', ''),
                                        'bias_example': st.session_state.get('bias_example', ''),
                                        'inclusive_suggestion': st.session_state.get('inclusive_suggestion', ''),
                                        'final_prompt': st.session_state.get('final_prompt', ''),
                                        'image_url': st.session_state.get('image_url', ''),
                                        'rating': st.session_state.get('rating'),
                                        'additional_feedback': st.session_state.get('additional_feedback',''),
                                        'random_profession': st.session_state.get('random_object', ''),
                                        'test_prompt': st.session_state.get('test_prompt', ''),
                                        'test_image_url': st.session_state.get('test_image_url', ''),
                                        'additional_rating': st.session_state.get('additional_rating')
                                    }
                                    
                                    # Check if Prolific ID already exists
                                    if check_prolific_id_exists(data['prolific_id']):
                                        st.error("Error: This Prolific ID has already been used.")
                                    else:
                                        # Insert data into the database
                                        if insert_user_data(data):
                                            st.success("Data saved successfully!")
                                            st.write("Here is your code to proceed.")
                                            st.code("1001")
                                            st.write("Please copy and paste this code into the text box in the questionnaire.")
                                            st.session_state['save_button_clicked'] = True
                                        else:
                                            st.error("Error: Failed to save data. Please try again.")
                            else:
                                st.write("Data has already been saved. Your completion code is:")
                                st.code("1001")
                                st.write("Please copy and paste this code into the text box in the questionnaire.")