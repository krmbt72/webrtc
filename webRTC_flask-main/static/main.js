let pc = new RTCPeerConnection();
let videoSource = 'camera';
let videoFilePath = '';

document.getElementById('videoSource').addEventListener('change', function() {
    videoSource = this.value;
    if (videoSource === 'file') {
        document.getElementById('videoFile').style.display = 'block';
    } else {
        document.getElementById('videoFile').style.display = 'none';
        videoFilePath = '';
    }
});

document.getElementById('videoFile').addEventListener('change', function(event) {
    const file = event.target.files[0];
    if (file) {
        const url = URL.createObjectURL(file);
        videoFilePath = url;
    }
});

// Set up event listeners for ICE candidates
pc.onicecandidate = event => {
    if (event.candidate) {
        console.log("Sending ICE candidate");
        fetch("/ice_candidate", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(event.candidate),
        });
    }
};

// Set up event listener for track
pc.ontrack = event => {
    const remoteVideo = document.getElementById("remoteVideo");
    if (remoteVideo.srcObject !== event.streams[0]) {
        remoteVideo.srcObject = event.streams[0];
        console.log("Received remote stream");
    }
};

async function createOffer() {
    console.log("Sending offer request");

    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    const offerResponse = await fetch("/offer", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({
            sdp: offer.sdp,
            type: offer.type,
            source: videoSource === 'file' ? videoFilePath : videoSource
        }),
    });

    const answer = await offerResponse.json();
    console.log("Received answer:", answer);

    await pc.setRemoteDescription(new RTCSessionDescription(answer));
}

// Start the WebRTC offer process when the button is clicked
document.getElementById('startButton').addEventListener('click', () => {
    let videoSource = document.getElementById('videoSource').value;
    let videoFileInput = document.getElementById('videoFile');

    let source = 'camera';
    if (videoSource === 'file') {
        const file = videoFileInput.files[0];
        if (file) {
            source = URL.createObjectURL(file);
        }
    }

    window.location.href = `/video_feed?source=${encodeURIComponent(source)}`;
});

