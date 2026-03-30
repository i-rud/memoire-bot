from scores import Scores
import os

def main():
    s = Scores()
    date = "20240327" 
    print(f"Testing refined score generation for {date}...")
    result = s.generate(date)
    print(f"Daily Leader: {result}")
    
    files = os.listdir("images/scores")
    print(f"Generated files: {files}")

if __name__ == "__main__":
    main()
