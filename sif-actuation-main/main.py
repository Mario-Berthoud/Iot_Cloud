#########################
#       ACTUATION       #
#########################

from base import LocalGateway, base_logger
from fastapi import Request
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

# Initialize the gateway
app = LocalGateway()
base_logger.info("Gateway initialized.")

# Function to send email directly
async def send_emergency_email(subject: str, body: str, recipients: list):
    """
    Sends an emergency email to the specified recipients.

    Args:
        subject (str): Subject of the email.
        body (str): Body of the email.
        recipients (list): List of recipient email addresses.
    """
    base_logger.info("Preparing to send emergency email.")
    try:
        # Email configuration
        smtp_server = "smtp.gmail.com"  # Gmail SMTP server
        smtp_port = 587
        sender_email = "iottrymario@gmail.com"  # Temporary email
        sender_password = "IoTTUMexample"  # Temporary password

        # Set up the email
        message = MIMEMultipart()
        message["From"] = sender_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))
        message["To"] = ", ".join(recipients)

        # Log the email details
        base_logger.info(f"Email prepared with subject: {subject} and recipients: {recipients}")

        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Secure the connection
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, message.as_string())

        base_logger.info(f"Email sent successfully to {recipients}")

    except Exception as e:
        base_logger.error(f"Failed to send email: {e}")
        raise

# Function to handle emergency notifications
async def emergency_notification_function(request: Request):
    """
    API endpoint to handle emergency notifications.

    Args:
        request (Request): Incoming HTTP request with emergency details.

    Returns:
        dict: Status of the operation.
    """
    base_logger.info("Emergency notification function triggered.")
    try:
        # Parse incoming request
        data = await request.json()
        base_logger.info(f"Received emergency data: {json.dumps(data, indent=2)}")

        # Construct email content
        subject = "Emergency Alert: Occupancy Condition Triggered"
        body = f"An emergency has been detected with the following details:\n{json.dumps(data, indent=2)}"
        recipients = ["recipient1@example.com", "recipient2@example.com"]  # Replace with actual recipients

        # Send the email
        await send_emergency_email(subject, body, recipients)

        # Log success
        base_logger.info("Emergency email sent successfully.")
        return {"status": "success", "message": "Emergency notification sent."}

    except Exception as e:
        # Log the error
        base_logger.error(f"Error in processing emergency notification: {e}")
        return {"status": "error", "message": str(e)}

# Deploy the emergency notification function
app.deploy(
    emergency_notification_function,
    name="emergency_notification_function",
    evts="EmergencyEvent",  # Event to trigger the function
    method="POST"  # HTTP method for the function
)

base_logger.info("Emergency notification function deployed and ready.")


#####################################
#           EXAMPLE CODE            #
#####################################

#First Skeleton

# from base import LocalGateway, base_logger, PeriodicTrigger, BaseEventFabric, ExampleEventFabric
# from fastapi import FastAPI, request

# app = LocalGateway()

# async def EmergencyNoticationFunction():
#     # Function
#     return 

# # app.deploy(base_fn, "fn-fabric", "CreateFn")
# app.deploy(EmergencyNoticationFunction,
#     name="str",
#     evts="List[str]",
#     method="str",
# )