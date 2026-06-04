import Foundation
import Vision
import ImageIO

struct OCRLine: Encodable {
    let text: String
    let confidence: Float
    let bbox: [Double]
}

guard CommandLine.arguments.count >= 2 else {
    fputs("Usage: swift scripts/vision_ocr.swift IMAGE_PATH\n", stderr)
    exit(2)
}

let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
guard let imageSource = CGImageSourceCreateWithURL(imageURL as CFURL, nil),
      let image = CGImageSourceCreateImageAtIndex(imageSource, 0, nil) else {
    fputs("Failed to load image: \(imageURL.path)\n", stderr)
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = false
request.recognitionLanguages = ["zh-Hant", "zh-Hans", "en-US"]

let handler = VNImageRequestHandler(cgImage: image, options: [:])
try handler.perform([request])

let lines = (request.results ?? []).compactMap { observation -> OCRLine? in
    guard let candidate = observation.topCandidates(1).first else {
        return nil
    }
    let bbox = observation.boundingBox
    return OCRLine(
        text: candidate.string,
        confidence: candidate.confidence,
        bbox: [
            Double(bbox.origin.x),
            Double(bbox.origin.y),
            Double(bbox.size.width),
            Double(bbox.size.height)
        ]
    )
}

let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .withoutEscapingSlashes]
let data = try encoder.encode(lines)
FileHandle.standardOutput.write(data)
FileHandle.standardOutput.write("\n".data(using: .utf8)!)
