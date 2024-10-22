import streamlit as st
from pymongo import MongoClient
from textblob import TextBlob
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import csv
from io import StringIO
import requests

# MongoDB connection setup
client = MongoClient("mongodb://localhost:27017/")
db = client["movie_db"]
reviews_collection = db["reviews"]
movies_collection = db["movies"]  # Collection to store movie metadata

# TMDb API configuration
TMDB_API_KEY = 'fb60ea478c32856c45015ed39cbd23c0'  # Replace with your TMDb API key
TMDB_BASE_URL = 'https://api.themoviedb.org/3'

# Function to analyze sentiment
def analyze_sentiment(review_text):
    blob = TextBlob(review_text)
    polarity = blob.sentiment.polarity
    if polarity > 0:
        return "Positive"
    elif polarity < 0:
        return "Negative"
    else:
        return "Neutral"

# Function to fetch movie details from TMDb
def fetch_movie_details(movie_title):
    search_url = f"{TMDB_BASE_URL}/search/movie?api_key={TMDB_API_KEY}&query={movie_title}"
    response = requests.get(search_url)
    if response.status_code == 200:
        data = response.json()
        if data['results']:
            return data['results'][0]  # Return the first result
    return None

# Streamlit UI
st.title("Movie Recommendation System")

# User Authentication (Simple Example)
if 'username' not in st.session_state:
    st.session_state['username'] = st.text_input("Enter Username")

# Review Submission
st.header("Submit Movie Review")
movie_title = st.text_input("Movie Title")
review_text = st.text_area("Your Review")

if st.button("Submit Review"):
    if st.session_state['username'] and movie_title and review_text:
        sentiment = analyze_sentiment(review_text)
        review = {
            "user": st.session_state['username'],
            "movie_title": movie_title,
            "review_text": review_text,
            "sentiment": sentiment,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        reviews_collection.insert_one(review)
        st.success(f"Review submitted! Sentiment: {sentiment}")
    else:
        st.error("Please provide username, movie title, and review.")

# Display Submitted Reviews
st.header("View Submitted Reviews")
reviews_list = list(reviews_collection.find({}))

if reviews_list:
    for review in reviews_list:
        st.subheader(review["movie_title"])
        st.write(f"Review by {review['user']}: {review['review_text']}")
        st.write(f"Sentiment: {review['sentiment']}")
        st.write(f"Submitted on: {review['timestamp']}")
        st.write("---")
else:
    st.info("No reviews submitted yet.")

# Trending Movies Visualization
st.header("Trending Movies")
trending_movies = reviews_collection.aggregate([
    {"$match": {"sentiment": "Positive"}},
    {"$group": {"_id": "$movie_title", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
])

trending_list = list(trending_movies)
if trending_list:
    movie_titles = [item['_id'] for item in trending_list]
    counts = [item['count'] for item in trending_list]

    plt.barh(movie_titles, counts)
    plt.xlabel('Number of Positive Reviews')
    plt.title('Trending Movies')
    st.pyplot(plt)
else:
    st.info("No trending movies available.")

# Recommended Movies
st.header("Recommended Movies")
if trending_list:
    for movie in trending_list:
        movie_details = fetch_movie_details(movie['_id'])
        if movie_details:
            st.subheader(movie_details['title'])
            st.write(f"Release Date: {movie_details['release_date']}")
            st.write(f"Overview: {movie_details['overview']}")
            if 'poster_path' in movie_details:
                st.image(f"https://image.tmdb.org/t/p/w500{movie_details['poster_path']}")
            st.write("---")

# Search Reviews by Movie Title
st.header("Search Reviews")
search_query = st.text_input("Enter a movie title to search reviews:")

if search_query:
    search_results = reviews_collection.find({"movie_title": {"$regex": search_query, "$options": "i"}})
    st.write(f"Showing results for '{search_query}':")

    for review in search_results:
        st.subheader(review["movie_title"])
        st.write(f"Review by {review['user']}: {review['review_text']}")
        st.write(f"Sentiment: {review['sentiment']}")
        st.write(f"Submitted on: {review['timestamp']}")
        st.write("---")
else:
    st.info("Enter a movie title to search reviews.")

# Export Reviews to CSV
st.header("Export Reviews")

if st.button("Export to CSV"):
    reviews = list(reviews_collection.find({}, {"_id": 0}))

    if reviews:
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=reviews[0].keys())
        writer.writeheader()
        writer.writerows(reviews)

        st.download_button(
            label="Download CSV",
            data=output.getvalue(),
            file_name='reviews.csv',
            mime='text/csv'
        )
    else:
        st.info("No reviews to export.")

# Option to delete all reviews
if st.button("Delete All Reviews"):
    reviews_collection.delete_many({})
    st.warning("All reviews deleted.")
