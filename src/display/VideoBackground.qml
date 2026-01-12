import QtQuick 2.15
import QtMultimedia 5.15

// Video Background Component (requires QtMultimedia)
Item {
    anchors.fill: parent

    Video {
        id: videoPlayer
        anchors.fill: parent
        source: displayModel && displayModel.videoFilePath ? displayModel.videoFilePath : ""
        fillMode: VideoOutput.PreserveAspectCrop
        autoPlay: true
        loops: MediaPlayer.Infinite
        muted: true  // Không phát âm thanh video nền
        
        onErrorChanged: {
            if (error !== MediaPlayer.NoError) {
                console.log("Video error:", errorString)
                visible = false
            }
        }
        
        onStatusChanged: {
            if (status === MediaPlayer.Loaded) {
                console.log("Video loaded successfully")
            }
        }
    }
}
