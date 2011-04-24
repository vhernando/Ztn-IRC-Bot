import sys
from optparse import OptionParser

from bot_module import Bot

parser = OptionParser()

parser.add_option("-c", "--conf",
                  action="store", type="string", dest="configuration")
(options, args) = parser.parse_args()

if options.configuration is None:
    myBot = Bot()
else:
    myBot = Bot(configuration=options.configuration)

myBot.main()
