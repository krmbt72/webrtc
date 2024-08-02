from flask import Flask, render_template, request, jsonify, Response
from aiortc import RTCPeerConnection, RTCSessionDescription
import uuid
import asyncio
import cv2
import logging
import time
from ultralytics import YOLO

app = Flask(__name__, static_url_path='/static')

# Global RTCPeerConnection instance
pcs = {}

# Load the YOLOv8 model
model = YOLO('bestv1.1.pt')  # Replace with your YOLOv8 model path if different

def generate_frames(source):
    if source == 'camera':
        video = cv2.VideoCapture(0)
    else:
        video = cv2.VideoCapture(source)
    
    if not video.isOpened():
        logging.error(f"Failed to open video source: {source}")
        return

    while True:
        start_time = time.time()
        success, frame = video.read()
        if not success:
            break
        else:
            # Process the frame using YOLOv8
            results = model(frame)[0]
            processed_frame = results.plot()  # Assuming render() returns list of processed frames

            # Encode the processed frame as JPEG
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame = buffer.tobytes()

            # Yield the frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

            elapsed_time = time.time() - start_time
            logging.debug(f"Frame generation time: {elapsed_time} seconds")

    video.release()

@app.route('/')
def index():
    return render_template('index.html')

async def handle_offer(params):
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    source = params.get("source", "camera")

    # Create an RTCPeerConnection instance
    pc = RTCPeerConnection()

    # Generate a unique ID for the RTCPeerConnection
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pc_id = pc_id[:8]

    # Store the RTCPeerConnection instance
    pcs[pc_id] = pc

    # Set the remote description and create an answer
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    # Prepare the response data with local SDP and type
    response_data = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type, "source": source}
    return jsonify(response_data)

@app.route('/offer', methods=['POST'])
def offer_route():
    params = request.json
    return asyncio.run(handle_offer(params))

@app.route('/answer', methods=['POST'])
def answer_route():
    params = request.json
    answer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # Set the remote description for the existing peer connection
    for pc in pcs.values():
        if not pc.remoteDescription:
            asyncio.run(pc.setRemoteDescription(answer))
            break

    return jsonify({"success": True})

@app.route('/ice_candidate', methods=['POST'])
def ice_candidate_route():
    candidate = request.json

    for pc in pcs.values():
        if not pc.remoteDescription:
            asyncio.run(pc.addIceCandidate(candidate))
            break

    return jsonify({"success": True})

@app.route('/video_feed')
def video_feed():
    source = request.args.get('source')
    return Response(generate_frames(source), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
