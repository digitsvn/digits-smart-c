import QtQuick 2.15
import QtQuick.Controls 2.15
import QtMultimedia 5.15

Rectangle {
    id: root
    width: 1024
    height: 768
    color: "#1a1a2e" // Dark background

    // Define signals
    signal manualButtonPressed()
    signal manualButtonReleased()
    signal autoButtonClicked()
    signal abortButtonClicked()
    signal modeButtonClicked()
    signal sendButtonClicked(string text)
    signal settingsButtonClicked()
    // Title bar signals
    signal titleMinimize()
    signal titleFullscreen()
    signal titleClose()
    signal titleDragStart(real mouseX, real mouseY)
    signal titleDragMoveTo(real mouseX, real mouseY)
    signal titleDragEnd()

    // 1. BACKGROUND LAYER (VIDEO / EMOTION)
    Item {
        id: bgLayer
        anchors.fill: parent

        // Video Background (hardware accelerated)
        Video {
            id: videoPlayer
            anchors.fill: parent
            visible: displayModel && displayModel.videoFilePath && displayModel.videoFilePath.length > 0
            source: visible ? displayModel.videoFilePath : ""
            fillMode: VideoOutput.Stretch  // Stretch để full màn hình, không crop
            autoPlay: true
            loops: MediaPlayer.Infinite
            muted: true  // Không phát âm thanh video nền
            
            // Tối ưu cho smooth loop
            onPositionChanged: {
                // Seek về đầu trước khi kết thúc để tránh giật
                if (duration > 0 && position > duration - 100) {
                    seek(0)
                }
            }
            
            onSourceChanged: {
                if (source && source.length > 0) {
                    console.log("Video source changed:", source)
                    play()
                }
            }
            
            onStatusChanged: {
                if (status === MediaPlayer.Loaded) {
                    console.log("Video loaded, starting playback")
                    play()
                } else if (status === MediaPlayer.EndOfMedia) {
                    // Đảm bảo loop mượt
                    seek(0)
                    play()
                }
            }
            
            onErrorChanged: {
                if (error !== MediaPlayer.NoError) {
                    console.log("Video error:", errorString)
                }
            }
        }

        // Emotion Loader (when video is not active)
        Loader {
            id: emotionLoader
            anchors.fill: parent
            visible: !videoPlayer.visible

            sourceComponent: {
                var path = displayModel ? displayModel.emotionPath : ""
                if (!path || path.length === 0) {
                    return emojiComponent
                }
                if (path.indexOf(".gif") !== -1) {
                    return gifComponent
                }
                if (path.indexOf(".") !== -1) {
                    return imageComponent
                }
                return emojiComponent
            }

            // GIF Component
            Component {
                id: gifComponent
                AnimatedImage {
                    anchors.fill: parent
                    fillMode: Image.PreserveAspectFit
                    source: displayModel ? displayModel.emotionPath : ""
                    playing: true
                    speed: 1.05
                    cache: true
                }
            }

            // Static Image
            Component {
                id: imageComponent
                Image {
                    anchors.fill: parent
                    fillMode: Image.PreserveAspectFit
                    source: displayModel ? displayModel.emotionPath : ""
                    cache: true
                }
            }

            // Emoji Text
            Component {
                id: emojiComponent
                Rectangle {
                    anchors.fill: parent
                    color: "#1a1a2e"  // Dark background instead of white
                    Text {
                        anchors.centerIn: parent
                        text: displayModel ? displayModel.emotionPath : "😊"
                        font.pixelSize: 120
                    }
                }
            }
        }
    }

    // 2. CONTENT OVERLAY (anchors-based; avoids QtQuick.Layouts dependency)
    Item {
        id: overlay
        anchors.fill: parent

        // Title Bar (Semi-transparent)
        Rectangle {
            id: titleBar
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 40
            color: "#80000000" // Semi-transparent dark
            z: 10

            MouseArea {
                anchors.fill: parent
                onPressed: root.titleDragStart(mouse.x, mouse.y)
                onPositionChanged: if (pressed) root.titleDragMoveTo(mouse.x, mouse.y)
                onReleased: root.titleDragEnd()
            }

            Row {
                id: windowControls
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                
                // Minimize button
                Rectangle {
                    width: 28; height: 28; radius: 6
                    color: "#20000000"
                    Text { anchors.centerIn: parent; text: "–"; font.pixelSize: 16; color: "#ffffff" }
                    MouseArea { anchors.fill: parent; onClicked: root.titleMinimize() }
                }
                
                // Fullscreen toggle button
                Rectangle {
                    width: 28; height: 28; radius: 6
                    color: "#20000000"
                    Text { 
                        anchors.centerIn: parent
                        text: "⛶"  // Fullscreen symbol
                        font.pixelSize: 14
                        color: "#ffffff" 
                    }
                    MouseArea { 
                        anchors.fill: parent
                        onClicked: root.titleFullscreen()
                    }
                }
                
                // Close button
                Rectangle {
                    width: 28; height: 28; radius: 6
                    color: "#E0FF0000"
                    Text { anchors.centerIn: parent; text: "×"; color: "white"; font.pixelSize: 16 }
                    MouseArea { anchors.fill: parent; onClicked: root.titleClose() }
                }
            }

            // Status Text
            Text {
                anchors.left: parent.left
                anchors.leftMargin: 15
                anchors.right: windowControls.left
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                text: displayModel ? displayModel.statusText : "Trạng thái: Chưa kết nối"
                font.pixelSize: 14
                font.bold: true
                color: "#ffffff"
                elide: Text.ElideRight
            }
        }

        // Bottom Controls Bar
        Rectangle {
            id: bottomBar
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 70
            color: "#CC1a1a2e" // Slightly transparent dark background

            Row {
                id: leftButtons
                anchors.left: parent.left
                anchors.leftMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                Button {
                    id: manualBtn
                    width: 140
                    height: 50
                    text: "Nhấn để nói"
                    visible: displayModel ? !displayModel.autoMode : true

                    background: Rectangle {
                        color: manualBtn.pressed ? "#003cb3" : "#165dff"
                        radius: 12
                    }
                    contentItem: Text {
                        text: manualBtn.text; color: "white"; font.bold: true;
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    onPressed: { manualBtn.text = "Thả để dừng"; root.manualButtonPressed() }
                    onReleased: { manualBtn.text = "Nhấn để nói"; root.manualButtonReleased() }
                }

                Button {
                    id: autoBtn
                    width: 140
                    height: 50
                    text: displayModel ? displayModel.buttonText : "Tự động"
                    visible: displayModel ? displayModel.autoMode : false

                    background: Rectangle { color: "#165dff"; radius: 12 }
                    contentItem: Text {
                        text: autoBtn.text; color: "white"; font.bold: true;
                        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                    }
                    onClicked: root.autoButtonClicked()
                }
            }

            Button {
                id: settingsBtn
                width: 40
                height: 50
                text: "..."
                anchors.right: parent.right
                anchors.rightMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                background: Rectangle { color: "#e5e6eb"; radius: 12 }
                onClicked: root.settingsButtonClicked()
            }

            // Input Field
            Rectangle {
                id: inputField
                anchors.left: leftButtons.right
                anchors.leftMargin: 12
                anchors.right: settingsBtn.left
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                height: 50
                color: "#2a2a3e"
                radius: 12
                border.color: "#444"

                TextInput {
                    id: textInput
                    anchors.fill: parent
                    anchors.leftMargin: 12
                    anchors.rightMargin: 12
                    verticalAlignment: TextInput.AlignVCenter
                    font.pixelSize: 14
                    color: "#ffffff"
                    selectByMouse: true
                    clip: true

                    Text {
                        anchors.fill: parent
                        text: "Nhập tin nhắn (Enter)..."
                        color: "#777"
                        visible: !textInput.text && !textInput.activeFocus
                        verticalAlignment: TextInput.AlignVCenter
                        leftPadding: 12
                    }

                    Keys.onReturnPressed: {
                        if (textInput.text.trim().length > 0) {
                            root.sendButtonClicked(textInput.text);
                            textInput.text = "";
                        }
                    }
                }
            }
        }

        // Chat History Area
        Item {
            id: chatArea
            anchors.top: titleBar.bottom
            anchors.bottom: bottomBar.top
            anchors.left: parent.left
            anchors.right: parent.right

            Column {
                anchors.bottom: parent.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.margins: 20
                spacing: 15

                // USER MESSAGE BUBBLE (Right)
                Item {
                    width: parent.width
                    height: userBubble.height
                    visible: displayModel && displayModel.userText && displayModel.userText.length > 0

                    Rectangle {
                        id: userBubble
                        anchors.right: parent.right
                        width: Math.min(Math.max(userTxt.implicitWidth + 30, 60), parent.width * 0.75)
                        height: userTxt.implicitHeight + 20
                        radius: 16
                        color: "#0e42d2" // Blue

                        Text {
                            id: userTxt
                            anchors.centerIn: parent
                            width: parent.width - 30
                            text: displayModel ? displayModel.userText : ""
                            color: "white"
                            font.pixelSize: 16
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignLeft
                        }
                    }
                }

                // AI MESSAGE BUBBLE (Left)
                Item {
                    width: parent.width
                    height: aiBubble.height
                    visible: displayModel && displayModel.ttsText && displayModel.ttsText !== "Đang chờ" && displayModel.ttsText.length > 0

                    Rectangle {
                        id: aiBubble
                        anchors.left: parent.left
                        width: Math.min(Math.max(aiTxt.implicitWidth + 30, 60), parent.width * 0.75)
                        height: aiTxt.implicitHeight + 20
                        radius: 16
                        color: "#2a2a3e" // Dark bubble
                        opacity: 0.90

                        Text {
                            id: aiTxt
                            anchors.centerIn: parent
                            width: parent.width - 30
                            text: displayModel ? displayModel.ttsText : ""
                            color: "#ffffff"
                            font.pixelSize: 16
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignLeft
                        }
                    }
                }
            }
        }
    }
}

