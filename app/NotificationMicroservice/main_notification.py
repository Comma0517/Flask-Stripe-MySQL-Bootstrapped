import sys
import json
import os
import stripe
from flask import request
import traceback

# Import all the things
from setup_app import app
from notification_action import NotificationAction

action = NotificationAction(app)

@app.route("/notification_read", methods=["PUT"])
def notification_read():
    return action.notification_read(request)

@app.route("/get_notifications/<user_id>", methods=["GET"])
def get_notifications(user_id):
    return action.get_notifications(user_id)

@app.route("/get_unread_notifications/<user_id>", methods=["GET"])
def get_unread_notifications(user_id):
    return action.get_unread_notifications(user_id)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=app.config['NOTIFICATION_PORT'])