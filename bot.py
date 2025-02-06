from methods import mattermost
import time
import sys

class Bot():

    def __init__(self):
        self.m = mattermost.MattermostMethods()

    def run(self):
        try:
            self.m.post_message("Security triage bot online")
            while True:
                self.m.process_mentions()
                time.sleep(self.m.polling_interval)
        except Exception as e:
            self.m.post_message(f"Error: {e}")
            sys.exit()

if __name__ == '__main__':
    b = Bot()
    b.run()