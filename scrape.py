import praw
import re
import fix_yahoo_finance as yf
import os
import jinja2
from operator import itemgetter

#praw Authintification
reddit = praw.Reddit(client_id='Reddit App ID', \
                     client_secret='Reddit Client ID', \
                     redirect_uri='http://localhost:8080',\
                     user_agent='WSB')


#subreddit instance to be used to grab comments
subreddit = reddit.subreddit('WallStreetBets')

#sets up empty lists and dictionaries that are needed

#holds the list of comment text barely used if at all?
comments_body = []

#holds the list of stock tickers
tickers = []

#holds tickers plus associated negative and positive counts
outlook = {}

#sorted list of of tickers and data that is ordered from least liked to most

puts = {}
#same as puts but most to least
calls = {}
#same as puts but sorted by total mentions instead of based on positive or negative
popular = {}


#blacklist of things that look like tickers but aren't. Note some things here are valid tickers but they are more
#commonly used as abreivations on WSB
not_tickers = [[],'DD', 'WSB', 'LOL', 'I', 'CNN', 'IV', 'IP', 'YOLO', 'TIL', 'EDIT', 'OTM', 'GOT', 'IPO']

#negative words subtract from faith positive words add
negative = ['put','short','down','sell','drop','fall','lose','bear','out','bad','mistake']
positive = ['call','long','up','buy','bull','in','good']


def FindTicker(text):
    temp = []

    #this regex finds anything that looks like a stock ticker so pretty much anything upper case 1-5 characters long
    #it's honestly kind of a nightmare 'cause I don't get regex
    temp = re.findall("(?:(?<=\A)|(?<=\s)|(?<=[$]))([A-Z]{1,5})(?=\s|$|[^a-zA-z])", text)

    #iterates over temp checking if each ticker is on the blacklist not_tickers if the ticker is not blacklisted it is
    #added to tickers
    for ticker in temp:
        if ticker not in not_tickers:
            if ticker not in tickers:
                tickers.append(ticker)
            else:
                temp.pop()
        if ticker in not_tickers:
            temp.pop()

    if temp ==[]:
        return tickers

    #this just removes any duplicates from the temp list
    for i in range(len(temp)-1):
        try:
            for j in range(i+1,len(temp)-1):
                if temp[i] == temp[j]:
                    try:
                        temp.pop(j)

                    except:
                        pass

        except:
            pass

    #tests each ticker by making a lookup call to fix_yahoo_finance if the call is empty it removes the ticker
    #I believe the try: except: block is depreciated at one point I was using another API that threw an error when a
    #bad lookup went through so I used that instead of checking if the returned value was empty.
    for i in range(len(temp)):
        try:
            test = yf.Ticker(tickers[-1-i])
            if test.info =={}:
                tickers.pop(-1-i)
        except Exception as e:
            print(e)

    #iterates over temp first making sure that the ticker is valid then looking at the comment the ticker was found in
    #and finding any words on the positive and negative lists then using that to add or subtract from the outlook value
    for ticker in temp:
        if ticker in tickers:
            #prints the ticker and the comment it was in so you can check wtf it's doing
            print("gonna do shit with " + ticker + ' based on \n' + text)
            if ticker not in outlook:

                #format is [faith, for, against, symbol, for + against]
                outlook[ticker]=[0, 0, 0, ticker, 0]
            if ticker in outlook:
                for word in negative:
                    if word in text.lower():
                        outlook[ticker][0] += -1
                        outlook[ticker][2] += 1
                        outlook[ticker][4] += 1
                for word in positive:
                    if word in text.lower():
                        outlook[ticker][0] += 1
                        outlook[ticker][1] += 1
                        outlook[ticker][4] += 1
    return tickers, outlook


def GetComments(number, number2):

    #looksup the number of comments and submissions that are passed to it
    #it just grabs the newest stuff through praw the max you can grab is 1000 for both
    comments = subreddit.comments(limit=number)
    titles = subreddit.new(limit=number2)

    #iterates over the comment body text, strips newline characters and then feeds the text to FindTicker() to extract
    #tickers and sentiment
    for i in comments:
        temp = i.body.strip('\n')
        comments_body.append(temp)
        FindTicker(temp)
    #same as above but with titles the actual text of the post is ignored. I added title crawling because the numbers
    #were a bit low for just comments and the titles were a work around for the thousand comment limit
    for i in titles:
        temp = i.title.strip('\n')
        comments_body.append(temp)
        FindTicker(temp)

def PickTickers(outlook):
    global puts
    puts = {}
    global calls
    calls = {}
    global popular
    popular = {}

    #ok so I had a bunch of elif statements but that was nasty and you had to add more if you wanted to scale this is
    #"better" but I don't know how lambdas work I stole this from google. Basically I am sorting the outlook dictionary
    #based on the value of the zeroth index held in the value of the outlook dictionary. This returns a list of tuples
    #which is formatted like so [(ticker, [faith, for, against, ticker, total]), (etc...)] so the correct way to
    #reference the amount of faith in the first ticker in the puts list is puts[0][1][0] to get the ticker it is
    #puts[0][1][3] the first [] refers to which put you want the first or second or third etc... the second [] is always
    #1 because it refers to the part of the tuple in the puts list which is alwasy going to be the second part that you
    #want the last brace refers to which part of the list contained in the second part of the tuple you want
    #to sum it up first brace picks a stock third brace picks the info you want.

    #highest faith first
    calls = sorted(outlook.items(), key = lambda x : x[1], reverse=True)
    #lowest faith first (faith can go negative)
    puts = sorted(outlook.items(), key = lambda x : x[1])
    #highest number of words total first
    popular = sorted(outlook.items(), key = lambda x : x[1][4], reverse=True)

def Generate():
    #jinja2 setup stuff

    #template file name
    template_filename = "display.html"
    #output file name
    rendered_filename = "index.html"

    #these are the vars that are used by Jinja to generate the html document
    render_vars = {

        #each of these blocks corosponds to one row of the chart in the generated HTML the format for the puts[][][] is
        #above
        'put1_sym': puts[0][1][3],
        'put1_total': puts[0][1][0],
        'put1_up': puts[0][1][1],
        'put1_down': puts[0][1][2],

        'put2_sym': puts[1][1][3],
        'put2_total': puts[1][1][0],
        'put2_up': puts[1][1][1],
        'put2_down': puts[1][1][2],

        'put3_sym': puts[2][1][3],
        'put3_total': puts[2][1][0],
        'put3_up': puts[2][1][1],
        'put3_down': puts[2][1][2],

        'put4_sym': puts[3][1][3],
        'put4_total': puts[3][1][0],
        'put4_up': puts[3][1][1],
        'put4_down': puts[3][1][2],

        'put5_sym': puts[4][1][3],
        'put5_total': puts[4][1][0],
        'put5_up': puts[4][1][1],
        'put5_down': puts[4][1][2],


        'call1_sym': calls[0][1][3],
        'call1_total': calls[0][1][0],
        'call1_up': calls[0][1][1],
        'call1_down': calls[0][1][2],

        'call2_sym': calls[1][1][3],
        'call2_total': calls[1][1][0],
        'call2_up': calls[1][1][1],
        'call2_down': calls[1][1][2],

        'call3_sym': calls[2][1][3],
        'call3_total': calls[2][1][0],
        'call3_up': calls[2][1][1],
        'call3_down': calls[2][1][2],

        'call4_sym': calls[3][1][3],
        'call4_total': calls[3][1][0],
        'call4_up': calls[3][1][1],
        'call4_down': calls[3][1][2],

        'call5_sym': calls[4][1][3],
        'call5_total': calls[4][1][0],
        'call5_up': calls[4][1][1],
        'call5_down': calls[4][1][2],

        'pop1': popular[0][1][3],
        'pop2': popular[1][1][3],
        'pop3': popular[2][1][3],
        'pop4': popular[3][1][3],
        'pop5': popular[4][1][3],
        'pop6': popular[5][1][3],
        'pop7': popular[6][1][3],
        'pop8': popular[7][1][3],
        'pop9': popular[8][1][3],
        'pop10': popular[9][1][3],

        #number of mentions for each popular stock well not quite mentions more of each bad or good word
        'val1': popular[0][1][4],
        'val2': popular[1][1][4],
        'val3': popular[2][1][4],
        'val4': popular[3][1][4],
        'val5': popular[4][1][4],
        'val6': popular[5][1][4],
        'val7': popular[6][1][4],
        'val8': popular[7][1][4],
        'val9': popular[8][1][4],
        'val10': popular[9][1][4],




    }

    #Jinja stuff that I don't understand I borrowed it from a tutorial and it works
    script_path = os.path.dirname(os.path.abspath(__file__))
    template_file_path = os.path.join(script_path, template_filename)
    rendered_file_path = os.path.join(script_path, rendered_filename)

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader(script_path))
    output_text = environment.get_template(template_filename).render(render_vars).encode("utf-8") #the .encode bit is vital if you want unicode support

    #output the generated html to the index.html file
    with open(rendered_file_path, "wb") as result_file: #the "wb" option is vital for unicode support
        result_file.write(output_text)

def main():
    #gets all the comments 1000 is the max for both of these parameters GetComments() also handles titles and sends the
    #text to FindTicker() which extracts and validates tickers
    #it takes a couple seconds even with really low values but big ones take a couple minutes
    #I would not run it with very few comments because some lists might throw index errors because they won't have enough tickers
    #low values also break puts and calls because of insufficent sentiment
    GetComments(1000,1000)
    #prints the list of tickers and outlooks so that you can check the sanity
    print(tickers)
    print(outlook)
    #sorts the outlook dictionary into puts calls and popular
    PickTickers(outlook)
    print(puts)
    print(calls)
    print(popular)
    #has Jinja2 generate the HTML
    Generate()

main()
