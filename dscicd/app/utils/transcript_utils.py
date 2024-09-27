def group_transcript_by_speaker(transcript):
    grouped_transcript = []
    current_speaker = None
    current_text = []
    current_start = None
    current_end = None

    for segment in transcript:
        speaker = segment["speaker"]
        words = segment["words"]

        if speaker != current_speaker:
            if current_speaker is not None:
                grouped_transcript.append({
                    "text": " ".join(current_text),
                    "start_timestamp": current_start,
                    "end_timestamp": current_end,
                    "speaker": current_speaker,
                    "speaker_id": segment["speaker_id"],
                    "language": segment["language"]
                })
            current_speaker = speaker
            current_text = []
            current_start = words[0]["start_timestamp"]

        current_text.append(" ".join(word["text"] for word in words))
        current_end = words[-1]["end_timestamp"]

    # Add the last segment
    if current_speaker is not None:
        grouped_transcript.append({
            "text": " ".join(current_text),
            "start_timestamp": current_start,
            "end_timestamp": current_end,
            "speaker": current_speaker,
            "speaker_id": segment["speaker_id"],
            "language": segment["language"]
        })

    return grouped_transcript
