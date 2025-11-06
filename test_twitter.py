"""Quick test script for Twitter API credentials."""

from uploaders.twitter_uploader import TwitterUploader

print("=" * 60)
print("TESTING TWITTER CONNECTION")
print("=" * 60)
print()

try:
    # Initialize Twitter uploader
    print("[1/3] Initializing Twitter uploader...")
    uploader = TwitterUploader()
    print("[OK] Twitter uploader initialized successfully!")
    print()

    # Get user info
    print("[2/3] Fetching your Twitter account info...")
    user_info = uploader.get_user_info()

    if user_info:
        print("[OK] Successfully connected to Twitter!")
        print()
        print("Account Information:")
        print(f"  Username: @{user_info['username']}")
        print(f"  Display Name: {user_info['name']}")
        print(f"  Followers: {user_info['followers']:,}")
        print(f"  Following: {user_info['following']:,}")
        print(f"  Total Tweets: {user_info['tweets']:,}")
        print()

        # Ask if user wants to post a test tweet
        print("[3/3] Testing tweet posting...")
        response = input("Do you want to post a test tweet? (yes/no): ").strip().lower()

        if response in ['yes', 'y']:
            print()
            print("Posting test tweet...")
            result = uploader.post_tweet("🎙️ Testing podcast automation! This is a test tweet from my new automation system. #PodcastAutomation")

            if result:
                print("[OK] Test tweet posted successfully!")
                print(f"  Tweet URL: {result['tweet_url']}")
                print()
                print("[!] Go check your Twitter to see the test tweet!")
                print("   You can delete it if you want - it was just a test.")
            else:
                print("[ERROR] Failed to post test tweet")
        else:
            print("Skipping test tweet.")
    else:
        print("[ERROR] Failed to get user info")
        print("Check your credentials in .env file")

except ValueError as e:
    print("[ERROR] Configuration Error:")
    print(f"  {e}")
    print()
    print("Make sure all four Twitter credentials are set in .env:")
    print("  - TWITTER_API_KEY")
    print("  - TWITTER_API_SECRET")
    print("  - TWITTER_ACCESS_TOKEN")
    print("  - TWITTER_ACCESS_SECRET")

except Exception as e:
    print("[ERROR]:")
    print(f"  {e}")
    print()
    print("This might mean:")
    print("  1. Credentials are incorrect")
    print("  2. App doesn't have Read and Write permissions")
    print("  3. Need to wait a few minutes for Twitter to activate the app")

print()
print("=" * 60)
