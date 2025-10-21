import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import FastAPI, Request, HTTPException, status
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

# --- Configuration ---
# Load environment variables from a .env file for local development
load_dotenv()

# Fetch config from environment variables
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
# IMPORTANT: Use a Google App Password here, not your regular password
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD") 
# This is a secret key to ensure only your Node.js app can call this service
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000") # A sensible default

# --- FastAPI App Initialization ---
app = FastAPI()

# --- Pydantic Data Validation Model ---
# This ensures the incoming request body has the correct data types
class UserPayload(BaseModel):
    email: EmailStr  # Automatically validates that it's a valid email format
    username: str

# --- API Endpoint Definition ---
@app.post("/send-welcome-email")
async def send_welcome_email_endpoint(payload: UserPayload, request: Request):
    """
    Receives user data from the Node.js registration service and sends a welcome email.
    This endpoint is protected by a secret API key sent in the request header.
    """
    # 1. Security Check: Validate the internal API key
    api_key = request.headers.get("x-internal-api-key")
    if not api_key or api_key != INTERNAL_API_KEY:
        print("🚨 Unauthorized attempt to access email service.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key"
        )

    # 2. Prepare and Send the Email
    print(f"📤 Received request to send email to: {payload.email}")
    try:
        # The actual email sending logic is in a separate function
        send_gmail(payload.email, payload.username)
        print(f"✅ Email successfully sent to {payload.email}")
        return {"message": f"Email sent successfully to {payload.email}"}
    except Exception as e:
        print(f"💥 Failed to send email to {payload.email}: {e}")
        # If sending fails, return an error to the calling service
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {str(e)}"
        )

def send_gmail(receiver_email: str, username: str):
    """
    Connects to Gmail's SMTP server and sends a formatted HTML email.
    """
    login_url = f"{FRONTEND_URL}/login?email={receiver_email}"

    message = MIMEMultipart("alternative")
    message["Subject"] = "Welcome to SMBJugaad LMS 🎉"
    message["From"] = f"SMBJugaad LMS <{SENDER_EMAIL}>"
    message["To"] = receiver_email

    # Create the HTML content of the email
    html = f"""
      <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; color: #333;">
        <h2 style="color: #4f46e5;">Welcome to SMBJugaad LMS, {username}!</h2>
        <p>We're excited to have you on board.</p>
        <p>You can now log in to start exploring your courses by clicking the button below:</p>
        <a href="{login_url}"
           style="display: inline-block; background-color: #4f46e5; color: white; padding: 12px 24px;
                  text-decoration: none; border-radius: 6px; font-weight: 600; margin: 10px 0;">
           Log in to SMBJugaad
        </a>
        <p style="font-size: 14px;">If the button doesn't work, you can copy and paste this link into your browser:</p>
        <p style="color: #555; word-break: break-all;">{login_url}</p>
        <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;"/>
        <p style="font-size: 12px; color: #999;">© 2025 SMBJugaad LMS</p>
      </div>
    """
    
    # Attach the HTML part to the MIMEMultipart message
    message.attach(MIMEText(html, "html"))

    # Create a secure SSL context
    context = ssl.create_default_context()

    # Use a 'with' statement to automatically manage the connection
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, message.as_string())

# This allows running the app locally for testing with 'python main.py'
# However, Render will use its own command.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
