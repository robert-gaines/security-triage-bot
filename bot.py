from methods import mattermost
import time

class Bot():

    def __init__(self):
        self.m = mattermost.MattermostMethods()

    def run(self):
        while True:
            self.m.process_mentions()
            time.sleep(self.m.polling_interval)

if __name__ == '__main__':
    b = Bot()
    b.run()