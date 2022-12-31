import os

from collections import deque

from flask import Flask, render_template, session, request, redirect
from flask_socketio import SocketIO, send, emit, join_room, leave_room

from helpers import login_required

app = Flask(__name__)
app.config["SECRET_KEY"] = "Secret key"
socketio = SocketIO(app)

channelsCreated = []
usersLogged = []
channelsMessages = dict()

channelsCreated.append('Public')
channelsMessages['Public'] = deque()

@app.route("/")
@login_required
def index():
    return render_template("index.html", channels=channelsCreated)

@app.route("/signin", methods=['GET','POST'])
def signin():
    ''' Save the username on a Flask session '''

    # Forget any username
    session.clear()

    username = request.form.get("username")
    
    if request.method == "POST":

        if len(username) < 1 or username == '':
            return render_template("error.html", message="Username empty")

        if username in usersLogged:
            return render_template("error.html", message="Username already exists")                   
        
        usersLogged.append(username)

        session['username'] = username  

        # Remember the user session on a cookie if the browser is closed.
        session.permanent = True

        return redirect("/channels/Public")
    else:
        return render_template("signin.html")

@app.route("/change", methods=['GET', 'POST'])
@login_required
def change():

    username = request.form.get("username")

    try:
        usersLogged.remove(session['username'])
    except ValueError:
        pass

    
    if request.method == "POST":

        if len(username) < 1 or username == '':
            return render_template("error.html", message="Username empty")

        if username in usersLogged:
            return render_template("error.html", message="Username already exists")                   
        
        usersLogged.append(username)

        session['username'] = username  

        return redirect("/")
    else:
        return render_template("change.html", channels= channelsCreated)

@app.route("/logout", methods=['GET', 'POST'])
@login_required
def logout():

    try:
        usersLogged.remove(session['username'])
    except ValueError:
        pass

    return redirect("signin")

@app.route("/create", methods=['GET','POST'])
@login_required
def create():
    ''' Create channel '''

    newChannel = request.form.get("channel")

    if request.method == "POST":

        if newChannel in channelsCreated:
            return render_template("error.html", message="That channel already exists!", channels= channelsCreated)
        if len(newChannel) == 0:
            return render_template("error.html", message="Channel empty", channels= channelsCreated)
        
        # Add channel to list
        channelsCreated.append(newChannel)

        # Add channel to global dict of channels with messages. Every channel is a deque to use popleft() method 

        channelsMessages[newChannel] = deque()
        
        return redirect("/channels/" + newChannel)
    
    else:

        return render_template("create.html", channels = channelsCreated)

@app.route("/channels/<channel>", methods=['GET','POST'])
@login_required
def enter_channel(channel):
    ''' Channel page '''

    user = session['username']

    # Updates user current channel
    session['current_channel'] = channel

    if channel not in channelsCreated:
        return redirect("/channels/Public")

    if request.method == "POST":
            
        return redirect("/")
    else:
        return render_template("channel.html", channels= channelsCreated, messages=channelsMessages[channel], usersLogged = usersLogged, user=user)


@socketio.on("joined", namespace='/')
def joined():
    ''' Announce user has entered to the channel '''
    
    # Save current channel to join room.
    room = session.get('current_channel')

    join_room(room)
    
    emit('status', {
        'userJoined': session.get('username'),
        'channel': room,
        'msg': session.get('username') + ' has joined the channel'}, 
        room=room)

@socketio.on('send message')
def send_msg(msg, timestamp):
    ''' Put the message in the channel '''

    # Send only to users on the same channel
    room = session.get('current_channel')

    # Save the message
    channelsMessages[room].append([timestamp, session.get('username'), msg])

    emit('announce message', {
        'user': session.get('username'),
        'timestamp': timestamp,
        'msg': msg}, 
        room=room)


@socketio.on("left", namespace='/')
def left():
    ''' Announce user has left the channel '''

    room = session.get('current_channel')

    leave_room(room)

    emit('status', {
        'msg': session.get('username') + ' has left the channel'}, 
        room=room)

if __name__ == "__main__":
    socketio.run(app)