import QtQuick 2.15
import QtQuick.Controls 2.15
import QtMultimedia 5.15
import QtGraphicalEffects 1.15

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

        // Video/Animation Background
        // Ưu tiên WebP/GIF (AnimatedImage - loop mượt hơn)
        // Fallback sang Video cho MP4
        
        property bool isAnimatedImage: {
            if (!displayModel || !displayModel.videoFilePath) return false
            var path = displayModel.videoFilePath.toLowerCase()
            return path.indexOf(".webp") !== -1 || path.indexOf(".gif") !== -1
        }
        
        // AnimatedImage cho WebP/GIF (loop mượt, không giật)
        AnimatedImage {
            id: animatedBg
            anchors.fill: parent
            visible: bgLayer.isAnimatedImage && displayModel && displayModel.videoFilePath && displayModel.videoFilePath.length > 0
            source: visible ? displayModel.videoFilePath : ""
            fillMode: Image.Stretch
            playing: true
            cache: true
            
            onStatusChanged: {
                if (status === AnimatedImage.Ready) {
                    console.log("AnimatedImage loaded:", source)
                }
            }
        }
        
        // Video cho MP4 (có thể giật khi loop)
        Video {
            id: videoPlayer
            anchors.fill: parent
            visible: !bgLayer.isAnimatedImage && displayModel && displayModel.videoFilePath && displayModel.videoFilePath.length > 0
            source: visible ? displayModel.videoFilePath : ""
            fillMode: VideoOutput.Stretch
            autoPlay: true
            loops: MediaPlayer.Infinite
            muted: true
            
            onSourceChanged: {
                if (source && source.length > 0) {
                    console.log("Video source:", source)
                    play()
                }
            }
            
            onErrorChanged: {
                if (error !== MediaPlayer.NoError) {
                    console.log("Video error:", errorString)
                }
            }
        }

        // Emotion Loader (when video/animation is not active)
        Loader {
            id: emotionLoader
            anchors.fill: parent
            visible: !videoPlayer.visible && !animatedBg.visible

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

        // Chat History Area - Both bubbles on RIGHT side
        Item {
            id: chatArea
            anchors.top: titleBar.bottom
            anchors.bottom: bottomBar.top
            anchors.left: parent.left
            anchors.right: parent.right

            Column {
                anchors.bottom: parent.bottom
                anchors.right: parent.right
                anchors.rightMargin: 20
                anchors.bottomMargin: 20
                width: Math.min(parent.width * 0.5, 450)  // Max 50% width or 450px
                spacing: 12

                // USER MESSAGE BUBBLE - Right aligned, gradient
                Rectangle {
                    id: userBubble
                    anchors.right: parent.right
                    visible: displayModel && displayModel.userText && displayModel.userText.length > 0
                    width: Math.min(Math.max(userTxt.implicitWidth + 36, 80), parent.width)
                    height: userTxt.implicitHeight + 20
                    radius: 18
                    
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "#667eea" }
                        GradientStop { position: 1.0; color: "#764ba2" }
                    }
                    
                    layer.enabled: true
                    layer.effect: DropShadow {
                        transparentBorder: true
                        horizontalOffset: 0
                        verticalOffset: 4
                        radius: 10
                        samples: 20
                        color: "#40667eea"
                    }

                    Text {
                        id: userTxt
                        anchors.centerIn: parent
                        width: parent.width - 28
                        text: displayModel ? displayModel.userText : ""
                        color: "white"
                        font.pixelSize: 14
                        font.weight: Font.Medium
                        wrapMode: Text.WordWrap
                    }
                }

                // AI MESSAGE BUBBLE - Also right aligned, dark glassmorphism
                Row {
                    anchors.right: parent.right
                    visible: displayModel && displayModel.ttsText && displayModel.ttsText !== "Đang chờ" && displayModel.ttsText.length > 0
                    spacing: 8
                    layoutDirection: Qt.RightToLeft  // Avatar on right

                    // Avatar on right side of bubble
                    Rectangle {
                        id: aiAvatar
                        width: 32
                        height: 32
                        radius: 16
                        anchors.bottom: parent.bottom
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#11998e" }
                            GradientStop { position: 1.0; color: "#38ef7d" }
                        }
                        Text {
                            anchors.centerIn: parent
                            text: "🤖"
                            font.pixelSize: 16
                        }
                    }

                    Rectangle {
                        id: aiBubble
                        width: Math.min(Math.max(aiTxt.implicitWidth + 36, 80), chatArea.width * 0.45)
                        height: aiTxt.implicitHeight + 20
                        radius: 18
                        color: "#CC1e1e2e"
                        border.color: "#40ffffff"
                        border.width: 1
                        
                        layer.enabled: true
                        layer.effect: DropShadow {
                            transparentBorder: true
                            horizontalOffset: 0
                            verticalOffset: 4
                            radius: 10
                            samples: 20
                            color: "#30000000"
                        }

                        Text {
                            id: aiTxt
                            anchors.centerIn: parent
                            width: parent.width - 28
                            text: displayModel ? displayModel.ttsText : ""
                            color: "#e8e8e8"
                            font.pixelSize: 14
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }
        }
    }
}

