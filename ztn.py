import sys

from bot_module import Bot

if len(sys.argv) > 1:
    myBot = Bot(configuration=sys.argv[1])
else:
    myBot = Bot()

#myBot = Bot(configure=conf)
myBot.main()
