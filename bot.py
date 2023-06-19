#!/usr/bin/env python3

#---------------------------------------------------#
#	Author: @alng                                   #
#	Version: 0.0                                    #
#                                                   #
#	Description:                                    #
#                                                   #
#     USC email verification bot                    #
#     For use on the USC CTF TEAM discord server    #
#                                                   #
#---------------------------------------------------#

# FOR EMAIL
import smtplib
import ssl
from email.message import EmailMessage

# FOR DISCORD
import discord
import asyncio
from discord.ext import commands

# FOR DATABASE
import json
import hashlib

#---------------#
# GLOBAL VARS	#
#---------------#

# SERVER/BOT ADMINS
admins = ["alng"]

# BOT SETUP
token_file = "./token.txt"
intents = discord.Intents.default()
intents.message_content = True
curr_activity = discord.Activity(name=f"Clash Royale", type=discord.ActivityType.playing)
bot = commands.Bot(command_prefix='/', intents=intents, activity=curr_activity)

# OTHER GLOBAL VARS
verified_role = "USC student"
pending_verification = []
verifydb_lock = asyncio.Lock()
server_db_file = "./serverdb.json"
serverdb_lock = asyncio.Lock()
serverdbfile_lock = asyncio.Lock()
server_db = []

#-------------------#
# HELPER FUNCTIONS  #
#-------------------#

# Get email credentials
def email_creds():
	with open("./mail.json", "r") as f:
		return json.loads(f.read())

# For hashing email
def hash_email(email):
	m = hashlib.sha256()
	m.update(bytes(email, 'utf-8'))
	return m.hexdigest() 

# Get a random code
def get_code():
	with open("/dev/urandom", "rb") as f:
		m = hashlib.sha256()
		m.update(f.read(0x20))
		return m.hexdigest()

# Load server database
def load_db():

	global server_db_file

	with open(server_db_file, "r") as f:
		return json.loads(f.read())

# Save server database
# NOTE: Must be called with serverdb_lock held
async def save_db():

	global server_db
	global server_db_file
	global serverdbfile_lock
	
	async with serverdbfile_lock:
		with open(server_db_file, "w") as f:
			f.write(json.dumps(server_db))

# Push db entry, hash email
async def push_db(entry):

	global server_db
	global serverdb_lock

	async with serverdb_lock:

		db_entry = {"name": entry["name"], "email": hash_email(entry["email"])}
		server_db.append(db_entry)
		await save_db()

# Delete a user from the db
async def pop_db(username):

	global server_db
	global serverdb_lock

	async with serverdb_lock:
		
		if username in [entry["name"] for entry in server_db]:
			del entry
			await save_db()
			return True

		else:
			return False

# Check if email is already registered with another user
async def check_db(email):

	global server_db
	global serverdb_lock
	cmp = hash_email(email)

	async with serverdb_lock:	

		if cmp in [entry["email"] for entry in server_db]:
			return True

		else:
			return False

# Get our bot's private token
def get_token():
	global token_file
	with open(token_file, "r") as f:
		return f.read()

# Parse email argument from verify cmd
def parse_email(msg, ctx):

	err = "Error: "
	email = "bottom_text"
	token_stream = []

	# basic check to see if email was supplied
	if not msg:
		err += "No email supplied...\n"
		err += "Sample usage syntax: /verify your_name@usc.edu"
		return [False, err]

	else:
		token_stream = msg.split()
		
	# now check for other errors
	try:
		# invalid num of args
		if (len(token_stream) != 1):
			err += "Invalid number of args.\n"
			err += "Sample usage syntax: /verify your_name@usc.edu"
			raise

		# no email supplied
		if (not token_stream):
			err += "No email supplied."
			raise
		
		# check for valid email
		if (valid_email(token_stream[0])):
			email = token_stream[0]
		else:
			err += "Invalid email format || Not a USC email."
			raise

	# handle error
	except:
		# check if err is empty
		if err == "Error: ":
			err += "Internal bot error. Pls kindly report this to @alng."
		# return error msg
		return [False, err]

	# all good, return email
	return [True, email]

# Check for valid email format && domain
def valid_email(email):

	maxlen_local = 64
	local = "joemama"
	domain = "domain.com"

	# NOTE: technically there are more valid chars and formats but we don't talk abt that...
	valid_local = list(range(ord("A"), ord("Z")+1))
	valid_local += list(range(ord("a"), ord("z")+1))
	valid_local += list(range(ord("0"), ord("9")+1))
	valid_local = [chr(c) for c in valid_local]
	valid_local += list("!#$%&'*+-/=?^_`{|}~")
	valid_set = set(valid_local)

	# do some basic format checking first
	if (email.count('@') != 1):
		return False

	try:
		[local, domain] = email.split("@")
	except:
		return False

	if len(local) > maxlen_local:
		return False

	if domain != "usc.edu":
		return False

	if not set(local).issubset(valid_set):
		return False

	return True

# Send verification email to user
def send_email(user):

	# setup email creds and addrs
	creds = email_creds()
	sender = creds["addr"]
	sender_pw = creds["pw"]
	receiver = user["email"]

	# SMTP server
	smtp_ctx = ssl.create_default_context()
	smtp_server = creds["server"]
	smtp_port = creds["server_port"]
	
	# format email message
	msg = EmailMessage()

	# setup headers
	msg["Subject"] = "USC CTF TEAM verification request"
	msg["From"] = sender
	msg["To"] = receiver

	# basic text version
	text_cnt = '''

	Dear @{uname},
	
		You are receiving this email in response to your verification request on the USC CTF Team Discord Server.

		Your verification code is: 
			{vcode}

		To complete your verification, please reply to the bot with the following command:
			" /code {vcode} "

		Thanks!

	XOXO <3,
	hog ridaaaa#8942

	'''.format(uname=user["name"], vcode=user["code"])

	# alt html version
	html_cnt = '''

	<html>
	<head>	
		<style>
			p.head {{
				font-size: 20px;
				margin-top: 30px;
				margin-bottom: 30px;
			}}
			
			h2 {{
				text-indent: 50px;
			}}

			p.cnt {{
				font-size: 16px;
				text-indent: 30px;
			}}
		</style>
	</head>
	<body>

		<p class="head">Dear @{uname}</p>

		<p class="cnt">You are receiving this email in response to your verification request on the USC CTF Team Discord Server.</p>
		
		<p class="cnt">Your verification code is:</p>
		
		<h2>{vcode}</h2>
		
		<p class="cnt">To complete your verification, please reply to the bot with the following command:</p>

		<h2>/code {vcode}</h2>

		<p class="cnt">Thanks!</p>

		<p class="head">
			XOXO <3,<br>
			hog ridaaaa#8942
		</p>

		<img src="https://static.wikia.nocookie.net/clashroyale/images/3/3b/Kiss_Hog.png/revision/latest/scale-to-width-down/95?cb=20180812195050" />
	
	</body>	
	</html>
	
	'''.format(uname=user["name"], vcode=user["code"])

	# set msg contents
	msg.set_content(text_cnt)		# text part
	msg.add_alternative(html_cnt, subtype="html")	# html part

	# setup server connection and send email
	with smtplib.SMTP(smtp_server, smtp_port) as s:
		s.ehlo()	# use extended proto
		s.starttls(context=smtp_ctx)
		s.ehlo()	# use extended proto
		s.login(sender, sender_pw)
		s.send_message(msg)

	print(msg)
	print(pending_verification)
	
	return

#-----------------------#
# START OF BOT COMMANDS	#
#-----------------------#

# SHOW All CMDS
@bot.command()
async def cmds(ctx):
	help_msg = '''
	Commands:
		/ping 	(Ping the bot)
		/echo 	(Echos back your message)
		/cmds 	(Show all available commands)
		/verify	(Verify your status as a USC student using email)
		/code	(Used to verify USC student status through code sent through email)
		/emote	(Does something cool...)
	'''
	await ctx.send(help_msg)

# PING TEST
@bot.command()
async def ping(ctx):
	await ctx.send("pong")

# ECHO TEST
@bot.command()
async def echo(ctx, *, content=str):
	await ctx.send(ctx.current_argument)

# POWEROFF BOT
@bot.command()
async def poweroff(ctx):

	global admins
	
	if ctx.author.name in admins:
		await ctx.send("Goodbye!")
		exit()
	else:
		await ctx.send("You do not have permission to use this cmd.")

# FOR INTERNAL DEBUGGING USE
@bot.command()
async def dbg(ctx, *, content=str):
	
	global admins

	# only bot admins are allowed to use this cmd
	if ctx.author.name in admins:
		print("Context obj:")
		print(vars(ctx))
		print("-"*0x20)
		print("Current message:")
		print(ctx.current_argument)
		print("-"*0x20)
		print("Sent by:")
		print(ctx.author)
		print("-"*0x20)
		await ctx.send("Debugging info printed.")
	else:
		await ctx.send("You do not have permission to use this cmd.")

# HEEHEEHEEHAW
@bot.command()
async def emote(ctx):
	#TODO: send emotes
	emote = "NOT IMPLEMENTED YET"
	await ctx.send(emote)

# VERIFY USC STUDENT WITH EMAIL
@bot.command()
async def verify(ctx, *, content=str):

	global verified_role
	global pending_verification
	global verifydb_lock

	user = ctx.author
	msg = ctx.current_argument
	reply_msg = ""

	# make sure they are not already verified
	if (verified_role in [r.name for r in user.roles]):
		await ctx.send("User: @{} is already verified.".format(user.name))
		return
	
	# get email
	[status, result] = parse_email(msg, ctx)

	# email OK
	if status:

		# create entry
		entry = {"name": user.name, "email": result, "code": get_code()}

		# check if email was previously used
		if await check_db(entry["email"]):
			reply_msg = "Email has already been used for verification. Please use another one."
			await ctx.send(reply_msg)
			return

		# grab lock
		async with verifydb_lock:

			entry_exists = False

			for u in pending_verification:

				if u["name"] == entry["name"]:

					# CASE 1: Entry exists, update verification code
					if u["email"] == entry["email"]:
						u["code"] = entry["code"]
						reply_msg = "Verification email resent. Please check your inbox."
						entry_exists = True
						break
					
					#CASE 2: Update email and verification code
					else:
						u["email"] = entry["email"]
						u["code"] = entry["code"]
						reply_msg = "Email updated for user: @{}\n".format(entry["name"])
						reply_msg += "Verification email resent. Please check your inbox." 
						entry_exists = True
						break
			
			# CASE 3: New verification request, add entry
			if not entry_exists:
				pending_verification.append(entry)
				reply_msg = "Verification email sent. Please check your inbox (spam folder)."

		# do the actual email sending stuff
		send_email(entry)
		await ctx.send(reply_msg)
		return

	# email ERROR
	else:
		await ctx.send(result)
		return

# VERIFY USC STUDENT EMAIL CODE
@bot.command()
async def code(ctx, *, content=str):
	
	global pending_verification
	global verifydb_lock
	global verified_role

	curr_user = ctx.author
	inp_code = ctx.current_argument

	# no code was given
	if not inp_code:
		ctx.send("No code was supplied, please try again.")
		return
	
	# make sure they are not already verified
	if (verified_role in [r.name for r in curr_user.roles]):
		await ctx.send("User: @{} is already verified.".format(curr_user.name))
		return

	# grab lock
	async with verifydb_lock:

		for u in pending_verification:
			
			if curr_user.name == u["name"] and inp_code == u["code"]:
				# success
				verification_entry = {"name": u["name"], "email": u["email"]};
				# update db
				await push_db(verification_entry)
				# add role
				student_role = discord.utils.get(ctx.guild.roles, name=verified_role)
				# make sure role exists
				if student_role is None:
					# this shd never happen
					await ctx.send("Internal bot error (role), pls report this to @alng.")
					return

				await curr_user.add_roles(student_role)
				await ctx.send("Verification successful! Congrats!")
				return

	# verification failed
	await ctx.send("Verification failed, please try again.")
	return

#---------------#
# MAIN FUNCTION	#
#---------------#

def main():

	#hog ridaaaa
	global bot
	global server_db

	server_db = load_db()
	token = get_token()
	bot.run(token)

	return

if __name__=="__main__":
	main()

