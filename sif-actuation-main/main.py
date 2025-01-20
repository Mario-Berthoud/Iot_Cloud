#########################
#       ACTUATION       #
#########################

from base import LocalGateway, base_logger

from fastapi import Request
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import logging
import time
import urllib3

VIZ_COMPONENT_URL = "http://192.168.1.132:9000"

logger = logging.getLogger(__name__)

def send_info(summary: str, detail: str, level: int) -> None:
    """
    Sends an informational item to the /api/info endpoint of the VIZ component.

    :param summary: Short description or summary of the information.
    :param detail: Detailed information (any serializable object).
    :param level: Priority or level of the information.
    """
    current_timestamp = int(time.time() * 1000)

    # Serialize 'message' to a JSON string if it's not already a string
    if isinstance(detail, str):
        msg_str = detail
    else:
        try:
            msg_str = json.dumps(detail, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize message to JSON: {e}")
            return

    info_item = {
        "timestamp": current_timestamp,
        "summary": summary,
        "detail": msg_str,
        "level": level
    }

    # Encode the info_item to JSON bytes
    try:
        encoded_data = json.dumps(info_item).encode('utf-8')
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to encode info item to JSON: {e}")
        return

    http = urllib3.PoolManager()
    url = f"{VIZ_COMPONENT_URL}/api/info"
    headers = {"Content-Type": "application/json"}

    try:
        response = http.request("POST", url, body=encoded_data, headers=headers)
        if response.status in [200, 201]:
            logger.info("Information item saved successfully.")
            if response.data:
                # Attempt to parse the response as JSON
                try:
                    response_data = json.loads(response.data.decode("utf-8"))
                    logger.info(f"Response: {response_data}")
                except json.JSONDecodeError:
                    logger.warning("Response data is not valid JSON.")
        else:
            logger.error(f"Failed to save info. HTTP Status: {response.status}")
            logger.error(f"Response: {response.data.decode('utf-8')}")
    except urllib3.exceptions.HTTPError as e:
        logger.error(f"HTTP error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


def send_todo(title: str, message: str, level: int) -> None:
    """
    Sends a ToDo item to the /api/todo endpoint of the VIZ component.

    :param title: Title of the ToDo item.
    :param message: Detailed message (any JSON-serializable object).
    :param level: Priority or level of the ToDo item.
    """
    # Generate the current Unix timestamp in milliseconds
    current_timestamp = int(time.time() * 1000)

    # Serialize 'message' to a JSON string if it's not already a string
    if isinstance(message, str):
        msg_str = message
    else:
        try:
            msg_str = json.dumps(message, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize message to JSON: {e}")
            return

    # Create the ToDo item
    todo_item = {
        "timestamp": current_timestamp,
        "titel": title,
        "msg": msg_str,
        "level": level
    }

    # Convert the Python dictionary to a JSON string
    encoded_data = json.dumps(todo_item).encode('utf-8')

    # Initialize the PoolManager
    http = urllib3.PoolManager()

    # Define the URL
    url = f"{VIZ_COMPONENT_URL}/api/todo"

    # Set the headers
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        # Send the POST request
        response = http.request(
            'POST',
            url,
            body=encoded_data,
            headers=headers
        )
        
        # Check the response status
        if response.status in [200, 201]:
            print("ToDo item saved successfully.")
            # Optionally, parse the response data
            if response.data:
                response_data = json.loads(response.data.decode('utf-8'))
                print("Response:", response_data)
        else:
            print(f"Failed to save ToDo item. Status Code: {response.status}")
            print("Response:", response.data.decode('utf-8'))
    except urllib3.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Initialize the gateway
app = LocalGateway()
base_logger.info("Gateway initialized.")

async def EmergencyNoticationFunction(request: Request):

    base_logger.info("EmergencyNoticationFunction called.")
    msg = await request.json()  # Parse the incoming JSON request
    base_logger.info(f"Function create_emergency_notification_function received data: {msg}")

    base_logger.info("Sending Emergency Notification.")
    send_todo("Emergency detected! ", msg, 2)  # Send the emergency notification 

    base_logger.info("Emergency Notification sent.")

    return

# Deploy the emergency notification function
app.deploy(
    EmergencyNoticationFunction, 
    name="EmergencyNoticationFunction", 
    evts="EmergencyEvent", 
    method="POST"
)
base_logger.info("create_emergency_notification_function app deployed.")