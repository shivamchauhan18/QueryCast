# NOTE -> Line no. 14, 27 contain confidential data make your own

# Import necessary libraries
import os
import re
from flask import Flask, request, jsonify
from flask_cors import CORS
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from googletrans import Translator
from dotenv import load_dotenv

# Load environment variables from .env file (used for secure storage of API keys)
load_dotenv()

# Environment configurations (used for compatibility/stability)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Initialize the Flask app
app = Flask(__name__)

# Enable CORS (Cross-Origin Resource Sharing) for the specified Chrome extension
CORS(app, origins=["chrome-extension://<unique_chrome_extention_id>"])

# Utility function to extract YouTube video ID from various URL formats
def extract_video_id(url):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    return match.group(1) if match else None

# Define the route to handle incoming POST requests for video question answering
@app.route("/api/askyou", methods=["POST"])
def askyou():
    data = request.get_json()  # Get the JSON payload from the request
    video_url = data.get("videoUrl")
    question = data.get("question")

    # Basic validation to ensure necessary inputs are present
    if not video_url or not question:
        return jsonify({"error": "Missing videoUrl or question."}), 400

    # Extract video ID from URL
    video_id = extract_video_id(video_url)
    if not video_id:
        return jsonify({"error": "Invalid YouTube URL."}), 400

    # Try fetching transcript in English or Hindi, fallback to default if not available
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "hi"])
    except Exception:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        except TranscriptsDisabled:
            return jsonify({"error": "No captions available for this video."}), 404

    # If transcript couldn't be fetched at all
    if not transcript_list:
        return jsonify({"error": "Transcript not available."}), 404

    # Combine transcript text into a single string
    original_text = " ".join(chunk["text"] for chunk in transcript_list)

    # Translate transcript to English (in case it's not already)
    translated = Translator().translate(original_text, dest="en")
    transcript = translated.text

    # Split the translated text into smaller chunks for processing
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
    chunks = text_splitter.create_documents([transcript])

    # Create vector embeddings using Gemini embeddings
    embedding_model = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_documents(chunks, embedding_model)

    # Create a retriever to find similar chunks relevant to the question
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 10})

    # Retrieve top relevant documents/chunks
    retrieved_docs = retriever.invoke(question)
    context_text = "\n\n".join(doc.page_content for doc in retrieved_docs)

    # Initialize the Gemini chat model
    gmodel = ChatGoogleGenerativeAI(model='gemini-2.0-flash')

    # Define the prompt template for LLM
    prompt = PromptTemplate(
        template="""
        You are a knowledgeable and helpful AI assistant.

        Your task is to answer the user's question using **only** the information from the transcript below.
        - If the answer is found in the transcript, provide a clear and concise response.
        - If the transcript does not contain enough information, respond with: "I'm not sure, cannot provide a confident answer."

        Context:
        {context}

        Question: {question}
        """,
        input_variables=['context', 'question']
    )

    # Format the final prompt with actual context and user question
    final_prompt = prompt.format(context=context_text, question=question)

    # Get response from the Gemini model
    response = gmodel.invoke(final_prompt)

    # Return the generated response to the frontend
    return jsonify({"response": response.content})

# Run the Flask app in debug mode
if __name__ == "__main__":
    app.run(debug=True)
