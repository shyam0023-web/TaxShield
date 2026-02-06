import requests

url = "http://127.0.0.1:8000/api/upload-notice"
file_path = "sample_notice.pdf"

try:
    with open(file_path, "rb") as f:
        files = {"file": ("sample_notice.pdf", f, "application/pdf")}
        data = {
            "fy": "2024-25",
            "section": 73
        }
        print(f"Uploading {file_path}...")
        response = requests.post(url, files=files, data=data)
        
        if response.status_code == 200:
            result = response.json()
            print("\n✅ SUCCESS!")
            print("-" * 50)
            print(f"EXTRACTED TEXT START: {result['extracted_text'][:100]}...")
            print(f"AUDIT PASSED: {result['audit_passed']}")
            print(f"CONFIDENCE: {result['confidence']}")
            print("-" * 50)
            print("REPLY PREVIEW:")
            print(result['reply'][:500])
        else:
            print(f"❌ FAILED: {response.text}")

except FileNotFoundError:
    print("❌ Error: sample_notice.pdf not found. Make sure you generated it!")
except Exception as e:
    print(f"❌ Error: {e}")
