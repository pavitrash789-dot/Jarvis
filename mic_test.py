import speech_recognition as sr

print("Starting microphone test...")

recognizer = sr.Recognizer()

microphones = sr.Microphone.list_microphone_names()

print("\nAvailable microphones:")
for i, name in enumerate(microphones):
    print(i, name)

print("\nOpening MacBook Air microphone...")

with sr.Microphone(device_index=0) as source:
    print("Microphone opened successfully.")
    print("Adjusting for background noise...")
    recognizer.adjust_for_ambient_noise(source, duration=1)

    print("\n🎤 SPEAK NOW...")
    
    try:
        audio = recognizer.listen(
            source,
            timeout=10,
            phrase_time_limit=8
        )

        print("Audio captured!")
        print("Converting speech to text...")

        text = recognizer.recognize_google(audio)

        print("\nYou said:")
        print(text)

    except sr.WaitTimeoutError:
        print("\n❌ No speech detected within 10 seconds.")

    except sr.UnknownValueError:
        print("\n❌ I heard something, but couldn't understand it.")

    except sr.RequestError as e:
        print("\n❌ Google speech service error:")
        print(e)

print("\nTest finished.")