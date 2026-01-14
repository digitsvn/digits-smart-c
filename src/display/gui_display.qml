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
        // KHÔNG dùng audio - để dành HDMI cho AI
        Video {
            id: videoPlayer
            anchors.fill: parent
            visible: !bgLayer.isAnimatedImage && displayModel && displayModel.videoFilePath && displayModel.videoFilePath.length > 0
            source: visible ? displayModel.videoFilePath : ""
            fillMode: VideoOutput.Stretch
            autoPlay: true
            loops: MediaPlayer.Infinite
            
            // Tắt hoàn toàn audio - để HDMI cho AI output
            muted: true
            volume: 0
            
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

        // Network Info Overlay (Top-Right - shows when hotspot/connected)
        Rectangle {
            id: networkOverlay
            anchors.top: parent.top
            anchors.topMargin: 50
            anchors.right: parent.right
            anchors.rightMargin: 15
            width: networkColumn.width + 24
            height: networkColumn.height + 24
            radius: 16
            color: displayModel && displayModel.networkMode === "hotspot" ? "#E05C258C" : "#E01a1a2e"
            border.color: displayModel && displayModel.networkMode === "hotspot" ? "#9C27B0" : "#333"
            border.width: 2
            visible: displayModel && displayModel.networkInfoText && displayModel.networkInfoText.length > 0
            z: 20
            
            // Glassmorphism effect
            layer.enabled: true
            layer.effect: DropShadow {
                transparentBorder: true
                horizontalOffset: 0
                verticalOffset: 4
                radius: 16
                samples: 25
                color: "#50000000"
            }
            
            Column {
                id: networkColumn
                anchors.centerIn: parent
                spacing: 10
                
                // Network Info Text
                Text {
                    id: networkText
                    text: displayModel ? displayModel.networkInfoText : ""
                    color: "#ffffff"
                    font.pixelSize: 14
                    font.weight: Font.Medium
                    horizontalAlignment: Text.AlignHCenter
                    lineHeight: 1.3
                }
                
                // QR Code Image (when available)
                Image {
                    id: qrCodeImage
                    source: displayModel && displayModel.qrCodePath ? displayModel.qrCodePath : ""
                    visible: displayModel && displayModel.qrCodePath && displayModel.qrCodePath.length > 0
                    width: 120
                    height: 120
                    fillMode: Image.PreserveAspectFit
                    anchors.horizontalCenter: parent.horizontalCenter
                    
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: -8
                        color: "white"
                        radius: 8
                        z: -1
                    }
                }
                
                // Scan hint
                Text {
                    visible: qrCodeImage.visible
                    text: "📷 Quét để cấu hình"
                    color: "#aaaaaa"
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                    anchors.horizontalCenter: parent.horizontalCenter
                }
            }
            
            // Pulse animation for hotspot mode
            SequentialAnimation on opacity {
                running: displayModel && displayModel.networkMode === "hotspot"
                loops: Animation.Infinite
                NumberAnimation { to: 1.0; duration: 1500 }
                NumberAnimation { to: 0.85; duration: 1500 }
            }
        }
        
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

                // USER MESSAGE BUBBLE (Right) - Modern glassmorphism style
                Item {
                    width: parent.width
                    height: userBubble.height + 10
                    visible: displayModel && displayModel.userText && displayModel.userText.length > 0

                    Rectangle {
                        id: userBubble
                        anchors.right: parent.right
                        width: Math.min(Math.max(userTxt.implicitWidth + 40, 80), parent.width * 0.8)
                        height: userTxt.implicitHeight + 24
                        radius: 20
                        
                        // Modern gradient
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#667eea" }
                            GradientStop { position: 1.0; color: "#764ba2" }
                        }
                        
                        // Soft shadow
                        layer.enabled: true
                        layer.effect: DropShadow {
                            transparentBorder: true
                            horizontalOffset: 0
                            verticalOffset: 4
                            radius: 12
                            samples: 25
                            color: "#40667eea"
                        }

                        Text {
                            id: userTxt
                            anchors.centerIn: parent
                            width: parent.width - 32
                            text: displayModel ? displayModel.userText : ""
                            color: "white"
                            font.pixelSize: 15
                            font.weight: Font.Medium
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignLeft
                        }
                        
                        // Tail for bubble
                        Canvas {
                            anchors.right: parent.right
                            anchors.rightMargin: -6
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 8
                            width: 12
                            height: 12
                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.fillStyle = "#764ba2"
                                ctx.beginPath()
                                ctx.moveTo(0, 0)
                                ctx.lineTo(12, 6)
                                ctx.lineTo(0, 12)
                                ctx.closePath()
                                ctx.fill()
                            }
                        }
                    }
                }

                // AI MESSAGE BUBBLE (Left) - Glassmorphism style
                Item {
                    width: parent.width
                    height: aiBubble.height + 10
                    visible: displayModel && displayModel.ttsText && displayModel.ttsText !== "Đang chờ" && displayModel.ttsText.length > 0

                    // AI Avatar
                    Rectangle {
                        id: aiAvatar
                        anchors.left: parent.left
                        anchors.bottom: aiBubble.bottom
                        width: 36
                        height: 36
                        radius: 18
                        gradient: Gradient {
                            GradientStop { position: 0.0; color: "#11998e" }
                            GradientStop { position: 1.0; color: "#38ef7d" }
                        }
                        
                        Text {
                            anchors.centerIn: parent
                            text: "🤖"
                            font.pixelSize: 18
                        }
                    }

                    Rectangle {
                        id: aiBubble
                        anchors.left: aiAvatar.right
                        anchors.leftMargin: 10
                        width: Math.min(Math.max(aiTxt.implicitWidth + 40, 80), parent.width * 0.75)
                        height: aiTxt.implicitHeight + 24
                        radius: 20
                        color: "#1e1e2e"
                        border.color: "#333"
                        border.width: 1
                        
                        // Glassmorphism effect
                        opacity: 0.95
                        
                        layer.enabled: true
                        layer.effect: DropShadow {
                            transparentBorder: true
                            horizontalOffset: 0
                            verticalOffset: 4
                            radius: 12
                            samples: 25
                            color: "#30000000"
                        }

                        Text {
                            id: aiTxt
                            anchors.centerIn: parent
                            width: parent.width - 32
                            text: displayModel ? displayModel.ttsText : ""
                            color: "#e0e0e0"
                            font.pixelSize: 15
                            font.weight: Font.Normal
                            wrapMode: Text.WordWrap
                            horizontalAlignment: Text.AlignLeft
                        }
                        
                        // Tail for bubble
                        Canvas {
                            anchors.left: parent.left
                            anchors.leftMargin: -6
                            anchors.bottom: parent.bottom
                            anchors.bottomMargin: 8
                            width: 12
                            height: 12
                            onPaint: {
                                var ctx = getContext("2d")
                                ctx.fillStyle = "#1e1e2e"
                                ctx.beginPath()
                                ctx.moveTo(12, 0)
                                ctx.lineTo(0, 6)
                                ctx.lineTo(12, 12)
                                ctx.closePath()
                                ctx.fill()
                            }
                        }
                    }
                }
            }
        }
    }
}

