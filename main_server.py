from flask import Flask, render_template
from flask_socketio import SocketIO, emit, send
import mss
from PIL import Image
import io
import time
import logging
import threading
import socketio as csio

logging.basicConfig(
    level=logging.DEBUG,  # Set the log level to DEBUG (can be INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Define log message format
    datefmt='%Y-%m-%d %H:%M:%S',  # Define date and time format
)



# Initialize Flask app and SocketIO
app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading", logger=True, engineio_logger=True)

clientsocketio = csio.Client()

# Serve the webpage

class MainServer:

    def __init__(self, dev:bool):

        self.n_clients = 10000
        self.connected = False
        self.dev = dev

        screenshot_thread = threading.Thread(name = "Screenshare", target=self.__handle_screenshot_share)
        screenshot_thread.start()

        proxy_thread = threading.Thread(name = "Proxy socket", target=self.__handle_proxy_socket)
        proxy_thread.start()
        logging.info("1 thread started")

        socketio.on_event("connect", self.onconnect)
        socketio.on_event("disconnect", self.ondisconnect)

        #app.add_url_rule("/", view_func=self.index)

        # Connect

        socketio.run(app, debug=False, port=8122)

    @socketio.on_error_default
    def socketerror(e):

        logging.error(f"Socket error: {e}")

    def index(self):
        return render_template("index.html")
    
    @staticmethod
    def __get_screenshot():
        try:
            with mss.mss() as sct:
                # Capture the first monitor (adjust index as needed)
                monitor = sct.monitors[2]
                screenshot = sct.grab(monitor)

                # Convert raw pixels to a PIL Image (RGB format)
                img = Image.frombytes('RGB', screenshot.size, screenshot.rgb)

                # Save image to a bytes buffer in PNG format
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85, optimize=True)
                png_bytes = buffer.getvalue()

                # Encode to base64
                return png_bytes
        except Exception as e:
            logging.error(f"Failed to screenshot: {e}")

    def __handle_request_screenshot(self, base64_data):
        try:
            # Capture screenshot using mss
        

                # Send the base64 string to the client
                clientsocketio.emit('screenshot_response', {'data': base64_data})
        except Exception as e:
            # Emit an error message if something goes wrong
            clientsocketio.emit('screenshot_response', {'error': str(e)})

    def __handle_screenshot_share(self):
        while True:
            start_time = time.time()

            if self.n_clients <= 0: 
                time.sleep(0.5)
                logging.info("No clients :(")
                continue
            if not self.connected: 
                logging.info("Not connected")
                time.sleep(0.5)
                continue

            data = self.__get_screenshot()
            logging.info("Screenshot")
            try:
                self.__handle_request_screenshot(base64_data=data)
            except Exception as e:
                logging.info(f"Failed to handle request: {e}")
            process_time = time.time() - start_time
            
            # Calculate the sleep time to maintain the target interval
            sleep_time = max(0, 0.5 - process_time)
            
            # Sleep to maintain the target interval
            time.sleep(sleep_time)
    def __handle_proxy_socket(self):
        ip_prod = "wss://remote-desktop-proxy.onrender.com/"
        ip_dev = "ws://127.0.0.1:5000"

        ip = ""
        if self.dev:
            ip = ip_dev
        else:
            ip = ip_prod

        clientsocketio.connect(ip, auth = {"token": "dev_token", "dist": "provider"})
        logging.info("Connected to server")
        self.connected = True
        clientsocketio.wait()


    def onconnect(self):
        logging.info("New client connected")
        self.n_clients += 1


    def ondisconnect(self):
        logging.info("Client disonnected")
        self.n_clients -= 1











# Run the application
if __name__ == '__main__':
    print("""Please choose what to connect to.
    1) Local server
    2) Live server (render platform)

    Indicate with '1' or '2'.
    """)
    a = input(" >").strip()
    dev = False
    if a == '1':dev=True
    elif a == '2':dev=False
    else: input("Invalid option. Defaulting to live server. >")
    m = MainServer(dev = dev)