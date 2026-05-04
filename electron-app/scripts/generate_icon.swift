import AppKit
import Foundation

let outputPath = CommandLine.arguments.dropFirst().first ?? "icon-master.png"
let outputURL = URL(fileURLWithPath: outputPath)

let size = NSSize(width: 1024, height: 1024)
let image = NSImage(size: size)

image.lockFocus()

let canvas = NSRect(origin: .zero, size: size)
NSColor(calibratedRed: 0.02, green: 0.06, blue: 0.14, alpha: 1.0).setFill()
canvas.fill()

let shadow = NSShadow()
shadow.shadowBlurRadius = 36
shadow.shadowOffset = NSSize(width: 0, height: -16)
shadow.shadowColor = NSColor(calibratedWhite: 0.0, alpha: 0.28)
shadow.set()

let gradientRect = NSRect(x: 96, y: 96, width: 832, height: 832)
let rounded = NSBezierPath(roundedRect: gradientRect, xRadius: 212, yRadius: 212)
let gradient = NSGradient(colors: [
    NSColor(calibratedRed: 0.05, green: 0.65, blue: 0.98, alpha: 1.0),
    NSColor(calibratedRed: 0.03, green: 0.40, blue: 0.83, alpha: 1.0),
    NSColor(calibratedRed: 0.04, green: 0.22, blue: 0.53, alpha: 1.0),
])!
gradient.draw(in: rounded, angle: 90)

NSGraphicsContext.saveGraphicsState()
let clip = NSBezierPath(roundedRect: gradientRect, xRadius: 212, yRadius: 212)
clip.addClip()

let glow = NSBezierPath(ovalIn: NSRect(x: 180, y: 620, width: 660, height: 260))
NSColor(calibratedRed: 0.83, green: 0.96, blue: 1.0, alpha: 0.18).setFill()
glow.fill()

let gridPath = NSBezierPath()
gridPath.lineWidth = 24
gridPath.lineCapStyle = .round
NSColor(calibratedRed: 0.86, green: 0.96, blue: 1.0, alpha: 0.14).setStroke()

for x in stride(from: 220.0, through: 820.0, by: 120.0) {
    gridPath.move(to: NSPoint(x: x, y: 190))
    gridPath.line(to: NSPoint(x: x, y: 840))
}
for y in stride(from: 220.0, through: 820.0, by: 120.0) {
    gridPath.move(to: NSPoint(x: 170, y: y))
    gridPath.line(to: NSPoint(x: 870, y: y))
}
gridPath.stroke()
NSGraphicsContext.restoreGraphicsState()

let cardRect = NSRect(x: 214, y: 210, width: 596, height: 604)
let card = NSBezierPath(roundedRect: cardRect, xRadius: 92, yRadius: 92)
NSColor(calibratedWhite: 1.0, alpha: 0.96).setFill()
card.fill()

let tabColor = NSColor(calibratedRed: 0.04, green: 0.30, blue: 0.66, alpha: 1.0)
tabColor.setFill()
NSBezierPath(roundedRect: NSRect(x: 292, y: 724, width: 90, height: 126), xRadius: 34, yRadius: 34).fill()
NSBezierPath(roundedRect: NSRect(x: 640, y: 724, width: 90, height: 126), xRadius: 34, yRadius: 34).fill()

let topBand = NSBezierPath(roundedRect: NSRect(x: 214, y: 608, width: 596, height: 206), xRadius: 92, yRadius: 92)
NSColor(calibratedRed: 0.08, green: 0.43, blue: 0.88, alpha: 1.0).setFill()
topBand.fill()

let maskRect = NSRect(x: 214, y: 608, width: 596, height: 120)
NSColor(calibratedRed: 0.08, green: 0.43, blue: 0.88, alpha: 1.0).setFill()
maskRect.fill()

let titleBar = NSBezierPath(roundedRect: NSRect(x: 278, y: 548, width: 468, height: 46), xRadius: 22, yRadius: 22)
NSColor(calibratedRed: 0.86, green: 0.94, blue: 1.0, alpha: 0.88).setFill()
titleBar.fill()

func drawTaskLine(y: CGFloat, width: CGFloat, alpha: CGFloat) {
    let path = NSBezierPath(roundedRect: NSRect(x: 298, y: y, width: width, height: 34), xRadius: 17, yRadius: 17)
    NSColor(calibratedRed: 0.08, green: 0.18, blue: 0.33, alpha: alpha).setFill()
    path.fill()
}

for row in 0..<4 {
    let y = CGFloat(470 - row * 88)
    let dot = NSBezierPath(ovalIn: NSRect(x: 294, y: y + 4, width: 26, height: 26))
    NSColor(calibratedRed: 0.08, green: 0.43, blue: 0.88, alpha: 1.0).setFill()
    dot.fill()

    drawTaskLine(y: y, width: 360, alpha: 0.88)
    drawTaskLine(y: y - 42, width: 250 + CGFloat(row * 22), alpha: 0.38)
}

let checkPath = NSBezierPath()
checkPath.lineWidth = 28
checkPath.lineCapStyle = .round
checkPath.lineJoinStyle = .round
NSColor(calibratedRed: 0.10, green: 0.82, blue: 0.63, alpha: 1.0).setStroke()
checkPath.move(to: NSPoint(x: 592, y: 250))
checkPath.line(to: NSPoint(x: 646, y: 198))
checkPath.line(to: NSPoint(x: 754, y: 324))
checkPath.stroke()

image.unlockFocus()

guard let tiffData = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiffData),
      let pngData = bitmap.representation(using: .png, properties: [:]) else {
    fputs("PNG 변환에 실패했습니다.\n", stderr)
    exit(1)
}

try pngData.write(to: outputURL)
print("아이콘 마스터 PNG 생성 완료: \(outputURL.path)")
