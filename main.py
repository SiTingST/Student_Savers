import json
import logging
import os

import datetime
from datetimerange import DateTimeRange

from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters,
                          ConversationHandler, CallbackQueryHandler)
from telegram import InlineKeyboardMarkup
from telegram import InlineKeyboardButton
import datetime
import psycopg2
import pytz
import urllib3
import roomSearch

# State definitions for top level conversation
SELECTING_ACTION, ROOM_SEARCHING, EVENT_HANDLING, HANDLING_EVENT = map(chr, range(4))
# State definitions for second level conversation
SELECT_BUILDING, SELECTING_LEVEL = map(chr, range(4, 6))
SELECT_CHECKIN_BUILDING = map(chr, range(6, 7))
SELECTING_ROOM = map(chr, range(7, 8))
FINISH_SELECTING_LEVEL2 = map(chr, range(8, 9))
SELECT_START_TIME = map(chr, range(9, 10))
SELECT_START_TIME2 = map(chr, range(10, 11))
SELECT_END_TIME = map(chr, range(11, 12))
SELECT_END_TIME2 = map(chr, range(12, 13))
CHECK_IN_TIME = map(chr, range(13, 14))
SUCCESSFUL_CHECK_IN = map(chr, range(14, 15))
CHECK_OUT = map(chr, range(15, 16))
SELECT_CHECK_OUT = map(chr, range(16, 17))

SELECT_OPTIONS_FOR_TIMING = map(chr, range(17, 18))

# State definitions for descriptions conversation
SELECT_OPTIONS_FOR_TIMING2 = map(chr, range(18, 19))

SELECTED_ROOM = map(chr, range(19, 20))

# Meta states
STOPPING, SHOWING = map(chr, range(20, 22))
END_SELECT_LEVEL = map(chr, range(22, 23))

# States for Event Handling
EVENT_DETAILS = map(chr, range(23, 24))
EVENT_DATE = map(chr, range(24, 25))
TIMER = map(chr, range(25, 26))
EVENT_DATE = map(chr, range(26, 27))
EMAIL = map(chr, range(27, 28))
CALENDAR = map(chr, range(29, 30))
CONFIRM_ADD_CAL = map(chr, range(30, 31))
EVENT_TIME = map(chr, range(31, 32))
HANDLING_EVENT2 = map(chr, range(32, 33))

import re
from scheduler import book_timeslot
from telegram_cal import create_calendar
from telegram_cal import process_calendar_selection

# Shortcut for ConversationHandler.END
END = ConversationHandler.END

bot_data = {
    'event_name': '',
    'event_detail': '',
    'event_date': '',
    'event_time': ''
}

PORT = int(os.environ.get('PORT', 5000))

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)
TOKEN = "1278045157:AAFjUYhhg50425eKh6cTKpF9APpzwjOdYiU"

# DB connection
con = psycopg2.connect(user="dzwnjonhbsmqyu",
                       password="781f607ee579c427c05b3b1e3346da5d655dd8187500cbf4ab2a9d58a80c73e7",
                       host="ec2-34-232-147-86.compute-1.amazonaws.com",
                       port="5432", database="dcqfivrciptlut")
cur = con.cursor()


# Top level conversation callbacks
def start(update, context):
    text = 'Hi, welcome to Studentsavers bot. Glad to have you here. What do you want to do? Room Searching is only ' \
           'available for SoC buildings. To abort, simply type /stop.'
    buttons = [[
        InlineKeyboardButton(text='Reminder System', callback_data=str(EVENT_HANDLING)),
        InlineKeyboardButton(text='Room Searching', callback_data=str(ROOM_SEARCHING))
    ]]

    context.chat_data["tele-username"] = update.message.from_user.username

    context.chat_data["date"] = datetime.datetime.now(pytz.timezone('Asia/Singapore'))
    context.chat_data["day"] = datetime.datetime.now(pytz.timezone('Asia/Singapore')).strftime("%A")

    keyboard = InlineKeyboardMarkup(buttons)

    update.message.reply_text(text=text, reply_markup=keyboard)

    logger.info('/start command triggered')

    return SELECTING_ACTION


def start2(update, context):
    text = 'Hi, welcome to Studentsavers bot. Glad to have you here. What do you want to do? Room Searching is only ' \
           'available for SoC buildings. To abort, simply type /stop.'
    buttons = [[
        InlineKeyboardButton(text='Reminder System', callback_data=str(EVENT_HANDLING)),
        InlineKeyboardButton(text='Room Searching', callback_data=str(ROOM_SEARCHING))
    ]]

    context.chat_data["date"] = datetime.datetime.now(pytz.timezone('Asia/Singapore'))
    context.chat_data["day"] = datetime.datetime.now(pytz.timezone('Asia/Singapore')).strftime("%A")

    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    logger.info('/start command triggered')

    return SELECTING_ACTION


def callNusmodApi(date, day, start_time, end_time, list_of_rooms, list_of_all_rooms):
    url = "https://api.nusmods.com/v2/2020-2021/semesters/1/venueInformation.json"

    http = urllib3.PoolManager()
    json_obj = http.request('GET', url)
    text = json.loads(json_obj.data.decode('UTF-8'))
    current_weekNo = roomSearch.return_weekNo(date)

    unavailableRoom = []

    for rooms in list_of_rooms:

        for index in range(len(text[rooms])):

            if text[rooms][index]["classes"]:

                for class_index in range(len(text[rooms][index]["classes"])):

                    weekNo = text[rooms][index]["classes"][class_index]["weeks"]

                    for num in weekNo:

                        if int(current_weekNo) == num:

                            if text[rooms][index]["classes"][class_index]["day"] == day:

                                start_hour = (text[rooms][index]["classes"][class_index]["startTime"][0:2])
                                start_min = (text[rooms][index]["classes"][class_index]["startTime"][2:4])

                                end_hour = (text[rooms][index]["classes"][class_index]["endTime"][0:2])
                                end_min = (text[rooms][index]["classes"][class_index]["endTime"][2:4])

                                currentDate = datetime.datetime.now(pytz.timezone('Asia/Singapore'))

                                lesson_start = datetime.datetime(
                                    int(currentDate.strftime("%Y")),
                                    int(currentDate.strftime("%m")),
                                    int(currentDate.strftime("%d")),
                                    int(start_hour), int(start_min), 0)

                                lesson_end = datetime.datetime(
                                    int(currentDate.strftime("%Y")),
                                    int(currentDate.strftime("%m")),
                                    int(currentDate.strftime("%d")),
                                    int(end_hour), int(end_min), 0)

                                lesson_range = DateTimeRange(pytz.utc.localize(lesson_start),
                                                             pytz.utc.localize(lesson_end))
                                searchTime = DateTimeRange(pytz.utc.localize(start_time), pytz.utc.localize(end_time))

                                if lesson_range.is_intersection(searchTime):
                                    unavailableRoom.append(rooms)

    start_time_string = start_time.strftime("%H%M")
    end_time_string = end_time.strftime("%H%M")

    date_string = date.strftime("%Y-%m-%d")
    values = (date_string, start_time_string, end_time_string)

    cur.execute("SELECT DISTINCT room_no FROM studentsavers.rooms WHERE date=%s AND start_time=%s AND end_time=%s;",
                values)

    sqlresult = cur.fetchall()
    unavailableRoom = list(dict.fromkeys(unavailableRoom))

    for r in unavailableRoom:
        list_of_rooms.remove(r)

    for items in list_of_rooms:
        list_of_all_rooms.append(items)

    available_rooms = list_of_all_rooms

    for checked_in_rooms in sqlresult:
        checked_in_rooms = ''.join(''.join(map(str, checked_in_rooms)).split('),'))
        for avail_room in available_rooms:
            if avail_room == checked_in_rooms:
                available_rooms.remove(avail_room)

    return available_rooms


def show_data(update, context):
    currentDate = datetime.datetime.now(pytz.timezone('Asia/Singapore'))

    print(context.chat_data["building"])
    print(context.chat_data["level"])

    if context.chat_data["building"] == "COMS1":
        room_label = roomSearch.com1_data(context.chat_data["level"])
        all_rooms = roomSearch.all_rooms_com1(context.chat_data["level"])

    else:
        room_label = roomSearch.com2_data(context.chat_data["level"])
        all_rooms = roomSearch.all_rooms_com2(context.chat_data["level"])

    print(room_label)
    available_rooms_data = callNusmodApi(context.chat_data["date"], context.chat_data["day"],
                                         context.chat_data["avail_start_time"],
                                         context.chat_data["callback_avail_end_time"],
                                         room_label, all_rooms)

    if len(available_rooms_data) > 0:

        text = "Rooms available are (From: " + roomSearch.convert_time_to_12hr(
            context.chat_data["callback_avail_start_time"]) + " to " + roomSearch.convert_time_to_12hr(
            context.chat_data["avail_end_time"]) + ") : "

        for rooms in available_rooms_data:
            text += '\n' + rooms

        context.chat_data["avail_rooms"] = available_rooms_data

        buttons = [[
            InlineKeyboardButton(text='Check in', callback_data='avail_room_check-in'),
        ]]


    else:
        text = " No available room found"

        context.chat_data["avail_rooms"] = available_rooms_data

        buttons = [[
            InlineKeyboardButton(text='Check in', callback_data='avail_room_check-in'),
            InlineKeyboardButton(text='Back', callback_data=str(END))
        ]]

    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SHOWING


def stop(update, context):
    """End Conversation by command."""
    update.message.reply_text('See you around!')

    return END


def end_second_level(update, context):
    """Return to top level conversation."""
    start(update, context)

    return END


# Second level conversation callbacks
def select_building(update, context):
    print("selected_building")
    text = 'Choose your action:'

    buttons = [[
        InlineKeyboardButton(text='COMS1', callback_data='COMS1'),
        InlineKeyboardButton(text='COMS2', callback_data='COMS2')
    ], [
        InlineKeyboardButton(text='Check In', callback_data='checkin'),
        InlineKeyboardButton(text='Check Out', callback_data='checkout')
    ],
        [
            InlineKeyboardButton(text='Back', callback_data="end_select_action")
        ]]

    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECT_BUILDING


def select_building_checkin(update, context):
    print("line 289 selected check in")
    print(update.callback_query.data)

    if update.callback_query.data == "end_checkin":
        return select_building(update, context)
    else:
        text = 'Choose a building:'
        buttons = [[
            InlineKeyboardButton(text='COMS1', callback_data='COMS1_check-in'),
            InlineKeyboardButton(text='COMS2', callback_data='COMS2_check-in')],

            [InlineKeyboardButton(text='Back', callback_data='end_checkin')]]

        keyboard = InlineKeyboardMarkup(buttons)
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

        return SELECT_CHECKIN_BUILDING


def createTimeButtons():
    buttons = [
        [InlineKeyboardButton(text='8am', callback_data='8')],
        [InlineKeyboardButton(text='9am', callback_data='9')],
        [InlineKeyboardButton(text='10am', callback_data='10')],
        [InlineKeyboardButton(text='11am', callback_data='11')],
        [InlineKeyboardButton(text='12pm', callback_data='12')],
        [InlineKeyboardButton(text='1pm', callback_data='13')],
        [InlineKeyboardButton(text='2pm', callback_data='14')],
        [InlineKeyboardButton(text='3pm', callback_data='15')],
        [InlineKeyboardButton(text='4pm', callback_data='16')],
        [InlineKeyboardButton(text='5pm', callback_data='17')],
        [InlineKeyboardButton(text='6pm', callback_data='18')],
        [InlineKeyboardButton(text='7pm', callback_data='19')],
        [InlineKeyboardButton(text='8pm', callback_data='20')],
        [InlineKeyboardButton(text='9pm', callback_data='21')],
        [InlineKeyboardButton(text='10pm', callback_data='22')],
        [InlineKeyboardButton(text='11pm', callback_data='23')]]

    keyboard = InlineKeyboardMarkup(buttons)

    return keyboard


def select_level(update, context):
    context.chat_data['building'] = update.callback_query.data

    text = 'Choose your level: '

    if update.callback_query.data == 'checkout':

        buttons = [];

        cur.execute("SELECT DISTINCT room_no FROM studentsavers.rooms WHERE username = %s",
                    [context.chat_data["tele-username"]])

        result = cur.fetchall()

        # check if result is empty:
        if len(result) > 0:
            text = 'Choose a room to check out from: '
            for room in result:
                rooms = ''.join(''.join(map(str, room)).split('),'))
                buttons.append([InlineKeyboardButton(text=str(rooms), callback_data=rooms)])
                keyboard = InlineKeyboardMarkup(buttons)
                update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

        else:
            text = 'No rooms to check out from'
            update.callback_query.edit_message_text(text=text)

        return CHECK_OUT
    else:
        if update.callback_query.data == 'COMS1':
            buttons = [[
                InlineKeyboardButton(text='Level B1', callback_data='level_B1'),
                InlineKeyboardButton(text='Level 1', callback_data='level_1')
            ], [
                InlineKeyboardButton(text='Level 2', callback_data='level_2'),
                InlineKeyboardButton(text='Back', callback_data='end_levels')
            ]]

        else:

            buttons = [[
                InlineKeyboardButton(text='Level 1', callback_data='level_1'),
                InlineKeyboardButton(text='Level 2', callback_data='level_2'),
            ], [
                InlineKeyboardButton(text='Level 3', callback_data='level_3'),
                InlineKeyboardButton(text='Level 4', callback_data='level_4')],
                [InlineKeyboardButton(text='Back', callback_data='end_levels')]]

        keyboard = InlineKeyboardMarkup(buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)
        return SELECTING_LEVEL


def select_level_checkin(update, context):
    print("line 394")
    print(update.callback_query.data)
    context.chat_data["building"] = update.callback_query.data.split("_")[0]

    if update.callback_query.data == "end_checkin":
        print("end check in")
        return select_building_checkin(update, context)

    else:
        text = 'Choose your level: '

        if update.callback_query.data == 'COMS1_check-in':

            buttons = [[
                InlineKeyboardButton(text='Level B1', callback_data='B1_check-in'),
                InlineKeyboardButton(text='Level 1', callback_data='1_check-in')
            ], [
                InlineKeyboardButton(text='Level 2', callback_data='2_check-in'),
                InlineKeyboardButton(text='Back', callback_data='end_checkin2')
            ]]

        else:
            buttons = [[
                InlineKeyboardButton(text='Level 1', callback_data='1_check-in'),
                InlineKeyboardButton(text='Level 2', callback_data='2_check-in')],

                [InlineKeyboardButton(text='Level 3', callback_data='3_check-in'),
                 InlineKeyboardButton(text='Level 4', callback_data='4_check-in')],

                [InlineKeyboardButton(text='Back', callback_data='end_checkin2')]]

        keyboard = InlineKeyboardMarkup(buttons)

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

        return SELECTING_ROOM


def choose_start_time(update, context):
    clicked_check_in_option = update.callback_query.data[0:3] == "COM"

    if update.callback_query.data == "end_levels":
        return select_building(update, context)

    else:
        if update.callback_query.data != "edit":
            context.chat_data["level"] = update.callback_query.data
        elif clicked_check_in_option:
            context.chat_data["chosen_room"] = update.callback_query.data

        text = "Please select the time." + "\n" + " From: "

        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=createTimeButtons())

        return SELECT_START_TIME


def choose_checkin_start_time(update, context):
    print("line 460")
    if update.callback_query.data != "edit":
        context.chat_data["chosen_room"] = update.callback_query.data

    text = "Please select the time." + "\n" + " From: "

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=createTimeButtons())

    return SELECT_START_TIME2


def choose_end_time(update, context):
    context.chat_data["callback_avail_start_time"] = update.callback_query.data

    text = "Please select the time." + "\n" + "From: " + roomSearch.convert_time_to_12hr(
        update.callback_query.data) + "\n " + "To: "

    currentDate = datetime.datetime.now(pytz.timezone('Asia/Singapore'))
    context.chat_data["avail_start_time"] = datetime.datetime(int(currentDate.strftime("%Y")),
                                                              int(currentDate.strftime("%m")),
                                                              int(currentDate.strftime("%d")),
                                                              int(update.callback_query.data), 0, 0)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=createTimeButtons())

    return SELECT_END_TIME


def choose_end_time2(update, context):
    context.chat_data["checkin_callback_avail_start_time"] = update.callback_query.data

    text = "Please select the time." + "\nFrom: " + roomSearch.convert_time_to_12hr(
        update.callback_query.data) + "\nTo: "

    currentDate = datetime.datetime.now(pytz.timezone('Asia/Singapore'))
    context.chat_data["checkin_avail_start_time"] = datetime.datetime(int(currentDate.strftime("%Y")),
                                                                      int(currentDate.strftime("%m")),
                                                                      int(currentDate.strftime("%d")),
                                                                      int(update.callback_query.data), 0, 0)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=createTimeButtons())

    return SELECT_END_TIME2


def confirm_timing(update, context):
    print("confirm timing 2?")
    currentDate = datetime.datetime.now(pytz.timezone('Asia/Singapore'))

    context.chat_data["avail_end_time"] = update.callback_query.data
    context.chat_data["callback_avail_end_time"] = datetime.datetime(int(currentDate.strftime("%Y")),
                                                                     int(currentDate.strftime("%m")),
                                                                     int(currentDate.strftime("%d")),
                                                                     int(update.callback_query.data), 0, 0)

    if int(context.chat_data["callback_avail_start_time"]) < int(update.callback_query.data):

        text = "Searching for room in " + context.chat_data["level"].replace('_', ' ') + " of " + context.chat_data[
            "building"] + "\nFrom: " + roomSearch.convert_time_to_12hr(
            context.chat_data["callback_avail_start_time"]) + "\nTo: " \
               + roomSearch.convert_time_to_12hr(update.callback_query.data);

        buttons = [[
            InlineKeyboardButton(text='Edit', callback_data='edit'),
            InlineKeyboardButton(text='Done', callback_data='continue'),
        ]]

    else:

        if int(context.chat_data["callback_avail_start_time"]) == int(update.callback_query.data):

            text = "Invalid time frame. (From: " + roomSearch.convert_time_to_12hr2(
                context.chat_data["callback_avail_start_time"]) + " to " + roomSearch.convert_time_to_12hr(
                update.callback_query.data) + ")" + "\nSelected start time cannot be the same as selected end time." \
                   + "\nDo click edit, to change the timeframe."

        else:

            text = "Invalid time frame. (From: " + roomSearch.convert_time_to_12hr(
                context.chat_data["callback_avail_start_time"]) + " to " + roomSearch.convert_time_to_12hr(
                update.callback_query.data) + ")" + "\nSelected start time cannot be more than selected end time." \
                   + "\nDo click edit, to change the timeframe."

        buttons = [[
            InlineKeyboardButton(text='Edit', callback_data='edit'),
        ]]

    keyboard2 = InlineKeyboardMarkup(buttons)
    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard2)

    return SELECT_OPTIONS_FOR_TIMING


def confirm_timing2(update, context):
    print("here confirm timng2")
    print(update.callback_query.data)

    currentDate = datetime.datetime.now(pytz.timezone('Asia/Singapore'))

    context.chat_data["checkin_avail_end_time"] = update.callback_query.data
    context.chat_data["checkin_callback_avail_end_time"] = datetime.datetime(int(currentDate.strftime("%Y")),
                                                                             int(currentDate.strftime("%m")),
                                                                             int(currentDate.strftime("%d")),
                                                                             int(update.callback_query.data), 0, 0)

    if int(context.chat_data["checkin_callback_avail_start_time"]) < int(update.callback_query.data):

        text = "Checking into " + context.chat_data["chosen_room"] + "\nFrom: " + \
               roomSearch.convert_time_to_12hr(context.chat_data["checkin_callback_avail_start_time"]) \
               + "\nTo: " + roomSearch.convert_time_to_12hr(update.callback_query.data);

        buttons = [[
            InlineKeyboardButton(text='Edit', callback_data='edit'),
            InlineKeyboardButton(text='Done', callback_data='continue'),
        ]]

        keyboard2 = InlineKeyboardMarkup(buttons)
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard2)

    else:

        text = "Invalid time frame. (From: " + roomSearch.convert_time_to_12hr(
            context.chat_data["checkin_callback_avail_start_time"]) + " to " + roomSearch.convert_time_to_12hr(
            update.callback_query.data) + ")" + "\nSelected start time cannot be more than selected end time." \
               + "\nDo click edit, to change the timeframe."

        buttons = [[
            InlineKeyboardButton(text='Edit', callback_data='edit'),
        ]]

        keyboard2 = InlineKeyboardMarkup(buttons)
        update.callback_query.answer()
        update.callback_query.edit_message_text(text=text, reply_markup=keyboard2)

    return SELECT_OPTIONS_FOR_TIMING2


# used for check-in
def show_all_level(update, context):
    if update.callback_query.data == "end_checkin2":
        print("line 557")
        return select_building_checkin(update, context)
    else:
        context.chat_data['level'] = update.callback_query.data
        buttons = []

        if context.chat_data["building"] == "COMS1":

            print("hello woeld")
            print(str(update.callback_query.data).split('_')[0])

            rooms_coms1 = roomSearch.checkin_all_rooms_com1("level " + str(update.callback_query.data).split('_')[0])
            text = 'Choose a room to check into: '

            for room in rooms_coms1:
                buttons.append([InlineKeyboardButton(text=str(room), callback_data=room)])

            keyboard = InlineKeyboardMarkup(buttons)
            update.callback_query.answer()
            update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

        else:
            rooms_coms2 = roomSearch.checkin_all_rooms_com2("level " + str(update.callback_query.data).split('_')[0])
            text = 'Choose a room to check into: '

            for room in rooms_coms2:
                buttons.append([InlineKeyboardButton(text=str(room), callback_data=room)])
                keyboard = InlineKeyboardMarkup(buttons)
                update.callback_query.answer()
                update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

        return FINISH_SELECTING_LEVEL2


def check_out_service(update, context):
    context.chat_data["checkout_room"] = update.callback_query.data
    text = 'Choose timing to check-out from:'

    cur.execute("SELECT DISTINCT start_time, end_time FROM studentsavers.rooms WHERE room_no = %s AND username = %s ",
                [update.callback_query.data, context.chat_data["tele-username"]])

    time_result = cur.fetchall()

    buttons = [];

    for timing in time_result:
        timing = ('').join(('-'.join(map(str, timing)).split('),')))
        buttons.append([InlineKeyboardButton(text=timing, callback_data=timing)])

    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text, reply_markup=keyboard)

    return SELECT_CHECK_OUT


def choose_check_out_time(update, context):
    date_text = context.chat_data['date'].strftime("%Y-%m-%d")

    cur.execute(
        "DELETE FROM studentsavers.rooms WHERE room_no = %s AND start_time = %s AND end_time = %s AND date =%s AND username = %s",
        [context.chat_data["checkout_room"], str(update.callback_query.data).split('-')[0],
         str(update.callback_query.data).split('-')[1],
         date_text, context.chat_data["tele-username"]])

    con.commit()

    text = "You have successfully check out." + "\nType /stop and /start to return to main menu."

    update.callback_query.edit_message_text(text=text)


def end_choose_action(update, context):
    """Return to top level conversation."""
    start2(update, context)

    return END


def stop_nested(update, context):
    """Completely end conversation from within nested conversation."""
    update.message.reply_text('Hope to see you again!.')

    return STOPPING


def confirm_time(update, context):
    text = 'Got it! Do click on the respective buttons to move on.'

    buttons = [[
        InlineKeyboardButton(text='Edit', callback_data='TIME'),
        InlineKeyboardButton(text='Done', callback_data=str(END)),
    ]]

    keyboard2 = InlineKeyboardMarkup(buttons)

    update.message.reply_text(text=text, reply_markup=keyboard2)

    return SELECT_OPTIONS_FOR_TIMING


def check_in_successfully(update, context):
    print("sucessful check in line 688")

    builing_text = str(context.chat_data['building']).split("_")[0]
    level_text = context.chat_data['level']
    room_no_text = context.chat_data['chosen_room']
    start_time_text = context.chat_data['checkin_avail_start_time'].strftime("%H%M")
    end_time_text = context.chat_data['checkin_callback_avail_end_time'].strftime("%H%M")

    date_text = context.chat_data['date'].strftime("%Y-%m-%d")
    username_text = context.chat_data["tele-username"]

    val = (
        builing_text, level_text, room_no_text, start_time_text, end_time_text, date_text,
        username_text)
    cur.execute("INSERT INTO"
                " studentsavers.rooms(building, level, room_no, start_time, end_time, date, username) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) "
                , val)
    con.commit()

    text = 'You have successfully check in to ' + room_no_text \
           + ' from ' + roomSearch.convert_time_to_12hr2(start_time_text) \
           + ' to ' + roomSearch.convert_time_to_12hr2(
        end_time_text) + "\nType /stop and /start to return to main menu."

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)


def select_available_room(update, context):
    text2 = 'Choose a room:'

    buttons = [];
    if len(context.chat_data["avail_rooms"]) > 0:
        for rooms in context.chat_data["avail_rooms"]:
            buttons.append([InlineKeyboardButton(text=rooms, callback_data=rooms)])

    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text2, reply_markup=keyboard)

    return SELECTED_ROOM


def checking_in(update, context):
    print("check in line 731")
    context.chat_data['chosen_room'] = update.callback_query.data

    builing_text = context.chat_data['building']
    level_text = context.chat_data['level']
    room_no_text = context.chat_data['chosen_room']
    start_time_text = context.chat_data['avail_start_time'].strftime("%H%M")
    end_time_text = context.chat_data['callback_avail_end_time'].strftime("%H%M")

    date_text = context.chat_data['date'].strftime("%Y-%m-%d")

    val = (
        builing_text, level_text, room_no_text, start_time_text, end_time_text, date_text,
        context.chat_data["tele-username"])
    cur.execute("INSERT INTO"
                " studentsavers.rooms(building, level, room_no, start_time, end_time, date, username) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) "
                , val)

    con.commit()

    text2 = 'You have successfully check in to ' + room_no_text \
            + ' from ' + roomSearch.convert_time_to_12hr2(start_time_text) + ' to ' \
            + roomSearch.convert_time_to_12hr2(end_time_text) + ".\nType /stop and /start to return to main menu."

    update.callback_query.edit_message_text(text=text2)


# Sending reminders

def event_handling(update, context):
    """Prompt users for event name"""
    text = 'Please enter the event name'

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    return HANDLING_EVENT


def edit_event_name(update, context):
    text = 'Please enter the event name'

    update.message.reply_text(text=text)

    return HANDLING_EVENT2


def set_event_name(update, context):
    message = update.message.text
    context.chat_data['event_name'] = message

    text = 'Please enter the event detail:'

    update.message.reply_text(text=text)

    return EVENT_DETAILS


def set_event_details(update, context):
    message = update.message.text
    context.chat_data['event_detail'] = message

    text = 'Please select a date'

    update.message.reply_text(text=text, reply_markup=create_calendar())

    return EVENT_DATE


def set_event_date(update, context):
    bot = context.bot

    selected, date = process_calendar_selection(update, context)

    context.chat_data['event_date'] = date.strftime("%Y-%m-%d")

    bot.send_message(chat_id=update.callback_query.from_user.id,
                     text="You selected %s" % (date.strftime("%Y-%m-%d")))

    text = 'Please enter the time in the following format: HH:MM'

    bot.send_message(chat_id=update.callback_query.from_user.id, text=text)

    return EVENT_TIME


def set_event_time(update, context):
    message = update.message.text

    context.chat_data['event_time'] = message

    text = 'Please send /confirm to continue, otherwise /edit'

    context.bot.send_message(chat_id=update.message.chat_id, text=text)

    # update.message.reply_text(text=text)

    return TIMER


def set_timer(update, context):
    # Add job to queue
    chat_id = update.message.chat_id

    context.chat_data['chat_id'] = chat_id

    event_datetime = context.chat_data['event_date'] + ' ' + context.chat_data['event_time']

    try:
        datetimeobj = datetime.datetime.strptime(event_datetime, '%Y-%m-%d %H:%M')
        # datetimeobj2 = datetimeobj - datetime.timedelta(days=1)
        today = datetime.datetime.now()
        diff = datetimeobj - today
        due = diff.total_seconds()
        logger.info(due)
        if due < 0:
            update.message.reply_text('Sorry we can not go back! Please try again')
            return edit_event_name(update, context)

        event_name = context.chat_data['event_name']
        event_detail = context.chat_data['event_detail']
        event_date = context.chat_data['event_date']
        event_time = context.chat_data['event_time']

        customize_stuff = {
            'chat_id': chat_id,
            'event_name': event_name,
            'event_detail': event_detail,
            'event_date': event_date,
            'event_time': event_time
        }

        new_job = context.job_queue.run_once(alarm, due, context=customize_stuff)
        context.chat_data['job'] = new_job

        update.message.reply_text('Reminder has been successfully set for ' + event_name)

        return add_to_calendar(update, context)

    except (IndexError, ValueError):
        update.message.reply_text('Wrong format. Please try again ' + event_name)
        return edit_event_name(update, context)


def alarm(context):
    event = 'Reminder \n\n' + context.job.context['event_name'] + '\n' + context.job.context['event_detail'] + '\non ' + \
            context.job.context['event_date'] + ' at ' + context.job.context['event_time']

    context.bot.send_message(context.job.context['chat_id'], text=event)


# Adding to google calendar

def add_to_calendar(update, context):
    text = 'Would you like to add the event to Google Calendar? \n/yes to continue and /no to go back to main menu.'

    update.message.reply_text(text=text)

    return CONFIRM_ADD_CAL


def check_email(email):
    regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
    if (re.search(regex, email)):
        logger.info("Valid email")
        return True
    else:
        logger.info("Invalid email")
        return False


def ask_confirm_add_cal(update, context):
    message = update.message.text

    context.chat_data['confirm_add_cal'] = message

    text = 'Please enter your email address. Otherwise, send /cancel'

    update.message.reply_text(text=text)

    return EMAIL


def ask_for_email(update, context):
    message = update.message.text

    context.chat_data['user_email'] = message

    text = 'Got it! Please send /confirm to add event to Google Calendar. \nOtherwise, send /cancel'

    update.message.reply_text(text=text)

    return CALENDAR


def confirm_add_to_calendar(update, context):
    input_email = context.chat_data['user_email']
    event_name = context.chat_data['event_name']
    event_detail = context.chat_data['event_detail']
    event_date = context.chat_data['event_date']
    event_time = context.chat_data['event_time']

    if (check_email(input_email) == True):
        response = book_timeslot(event_name, event_detail, event_date, event_time, input_email)
        if (response == True):
            text = 'Event has been added to Google Calendar'
        else:
            text = 'Errors'

        update.message.reply_text(text)
        return end_second_level(update, context)
    else:
        text = 'Please enter a valid email'
        update.message.reply_text(text)

        return edit_event_name(update, context)


def help(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text('If the bot is stuck, type /stop and /start to restart the bot.')


# Error handler
def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    selection_handlers3 = [
        CallbackQueryHandler(choose_checkin_start_time, pattern='^' + 'edit' + '$'),
        CallbackQueryHandler(check_in_successfully, pattern='^' + 'continue' + '$')
    ]

    checking_in_convo2 = ConversationHandler(

        entry_points=[CallbackQueryHandler(choose_checkin_start_time)],

        states={

            SELECT_START_TIME2: [CallbackQueryHandler(choose_end_time2,
                                                      pattern='^{0}$|^{1}$|^{2}$|^{3}$|^{4}$|^{5}$|^{6}$|^{7}$|^{'
                                                              '8}$|^{9}$|^{10}$|^{11}$|^{12}$|^{13}$|^{14}$|^{15}$'
                                                      .format('8',
                                                              '9',
                                                              '10',
                                                              '11',
                                                              '12',
                                                              '13',
                                                              '14',
                                                              '15',
                                                              '16',
                                                              '17',
                                                              '18',
                                                              '19',
                                                              '20',
                                                              '21',
                                                              '22',
                                                              '23'))],

            SELECT_END_TIME2: [CallbackQueryHandler(confirm_timing2,
                                                    pattern='^{0}$|^{1}$|^{2}$|^{3}$|^{4}$|^{5}$|^{6}$|^{7}$|^{'
                                                            '8}$|^{9}$|^{10}$|^{11}$|^{12}$|^{13}$|^{14}$|^{15}$'.format(
                                                        '8',
                                                        '9',
                                                        '10',
                                                        '11',
                                                        '12',
                                                        '13',
                                                        '14',
                                                        '15',
                                                        '16',
                                                        '17',
                                                        '18',
                                                        '19',
                                                        '20',
                                                        '21',
                                                        '22',
                                                        '23'))],

            SELECT_OPTIONS_FOR_TIMING2: selection_handlers3,
            SUCCESSFUL_CHECK_IN: [CallbackQueryHandler(check_in_successfully)]

        },

        fallbacks=[
            CallbackQueryHandler(checking_in),
            CommandHandler('stop', stop_nested)
        ],
        map_to_parent={
            # Return to second level menu

            # End conversation alltogether
            STOPPING: STOPPING,
        }
    )
    selection_handlers2 = [
        CallbackQueryHandler(show_data, pattern='^' + 'continue' + '$'),
        CallbackQueryHandler(choose_start_time, pattern='^' + 'edit' + '$'),

    ]

    select_building_option_handler = [
        CallbackQueryHandler(select_level, pattern='^{0}$|^{1}$|^{2}$'.format('COMS1',
                                                                              'COMS2',
                                                                              'checkout',
                                                                              )),
        CallbackQueryHandler(select_building_checkin, pattern='^{0}$|^{1}$'.format('checkin', 'end_checkin'))]

    # Set up third level ConversationHandler (collecting features)
    input_time_convo = ConversationHandler(
        entry_points=[CallbackQueryHandler(choose_start_time,
                                           pattern='^{0}$|^{1}$|^{2}$|^{3}$|^{4}$|^{5}$|^{6}$|^{7}$'
                                           .format('end_levels',
                                                   'level_B1',
                                                   'level_1',
                                                   'level_2',
                                                   'level_3',
                                                   'level_4',
                                                   'end_checkin',
                                                   'end_checkin2'))],

        states={

            SELECT_BUILDING: select_building_option_handler,
            SELECT_CHECKIN_BUILDING: [CallbackQueryHandler(select_level_checkin,
                                                           pattern='^{0}$|^{1}$|^{2}$'.format('COMS1_check-in',
                                                                                              'COMS2_check-in',
                                                                                              'end_checkin'))],
            SELECT_START_TIME: [CallbackQueryHandler(choose_end_time,
                                                     pattern='^{0}$|^{1}$|^{2}$|^{3}$|^{4}$|^{5}$|^{6}$|^{7}$|^{'
                                                             '8}$|^{9}$|^{10}$|^{11}$|^{12}$|^{13}$|^{14}$|^{15}$'
                                                     .format('8',
                                                             '9',
                                                             '10',
                                                             '11',
                                                             '12',
                                                             '13',
                                                             '14',
                                                             '15',
                                                             '16',
                                                             '17',
                                                             '18',
                                                             '19',
                                                             '20',
                                                             '21',
                                                             '22',
                                                             '23'))],

            SELECT_END_TIME: [CallbackQueryHandler(confirm_timing,
                                                   pattern='^{0}$|^{1}$|^{2}$|^{3}$|^{4}$|^{5}$|^{6}$|^{7}$|^{'
                                                           '8}$|^{9}$|^{10}$|^{11}$|^{12}$|^{13}$|^{14}$|^{15}$'.format(
                                                       '8',
                                                       '9',
                                                       '10',
                                                       '11',
                                                       '12',
                                                       '13',
                                                       '14',
                                                       '15',
                                                       '16',
                                                       '17',
                                                       '18',
                                                       '19',
                                                       '20',
                                                       '21',
                                                       '22',
                                                       '23'))],
            SHOWING: [CallbackQueryHandler(select_available_room, pattern='^' + 'avail_room_check-in' + '$')],
            SELECT_OPTIONS_FOR_TIMING: selection_handlers2,
            SELECTED_ROOM: [CallbackQueryHandler(checking_in)]

        },

        fallbacks=[
            CommandHandler('stop', stop_nested)
        ],

        map_to_parent={
            # Return to second level menu

            # End conversation alltogether
            STOPPING: STOPPING,
        }
    )

    select_building_option_handler = [
        CallbackQueryHandler(select_level, pattern='^{0}$|^{1}$|^{2}$'.format('COMS1',
                                                                              'COMS2',
                                                                              'checkout',
                                                                              )),

        CallbackQueryHandler(select_building_checkin, pattern='^{0}$|^{1}$'.format('checkin', 'end_checkin'))]

    # Set up second level ConversationHandler (selecting building)
    choose_building_convo = ConversationHandler(
        entry_points=[CallbackQueryHandler(select_building,
                                           pattern='^' + str(ROOM_SEARCHING) + '$')],

        states={
            SELECT_BUILDING: select_building_option_handler,

            SELECT_CHECKIN_BUILDING: [CallbackQueryHandler(select_level_checkin,
                                                           pattern='^{0}$|^{1}$|^{2}$'.format('COMS1_check-in',
                                                                                              'COMS2_check-in',
                                                                                              'end_checkin'))],

            SELECTING_LEVEL: [input_time_convo],
            SELECTING_ROOM: [CallbackQueryHandler(show_all_level, pattern='^{0}$|^{1}$|^{2}$|^{3}$|^{4}$|^{5}$|^{6}$'
                                                  .format('B1_check-in',
                                                          '1_check-in',
                                                          '2_check-in',
                                                          '3_check-in',
                                                          '4_check-in',
                                                          'end_checkin2',
                                                          'end_levels'
                                                          ))],

            FINISH_SELECTING_LEVEL2: [checking_in_convo2],

            CHECK_OUT: [CallbackQueryHandler(check_out_service)],
            SELECT_CHECK_OUT: [CallbackQueryHandler(choose_check_out_time)]
        },

        fallbacks=[

            CallbackQueryHandler(end_choose_action, pattern='^' + 'end_select_action' + '$'),

            CommandHandler('stop', stop_nested)
        ],

        map_to_parent={
            # After showing data return to top level menu
            END_SELECT_LEVEL: SELECTING_ACTION,
            SHOWING: SHOWING,
            # Return to top level menu
            END: SELECTING_ACTION,
            # End conversation alltogether
            STOPPING: END,
        }
    )

    # Event handling ConversationHandler
    event_handling_convo = ConversationHandler(
        entry_points=[CallbackQueryHandler(event_handling,
                                           pattern='^' + str(EVENT_HANDLING) + '$')],
        states={
            HANDLING_EVENT: [
                MessageHandler(Filters.command, stop_nested),
                MessageHandler(Filters.text, set_event_name)
            ],
            EVENT_DETAILS: [
                MessageHandler(Filters.command, stop_nested),
                MessageHandler(Filters.text, set_event_details)
            ],
            EVENT_DATE: [CallbackQueryHandler(set_event_date)],
            EVENT_TIME: [
                MessageHandler(Filters.command, stop_nested),
                MessageHandler(Filters.text, set_event_time)
            ],
            TIMER: [
                CommandHandler('confirm', set_timer, pass_args=True, pass_job_queue=True, pass_chat_data=True),
                CommandHandler('edit', edit_event_name)
            ],
            CONFIRM_ADD_CAL: [
                CommandHandler('yes', ask_confirm_add_cal),
                CommandHandler('no', end_second_level)
            ],
            EMAIL: [
                CommandHandler('cancel', end_second_level),
                MessageHandler(Filters.text, ask_for_email)
            ],
            CALENDAR: [
                CommandHandler('confirm', confirm_add_to_calendar),
                CommandHandler('cancel', end_second_level)
            ],
            HANDLING_EVENT2: [
                MessageHandler(Filters.command, stop_nested),
                MessageHandler(Filters.text, set_event_name)
            ],
        },

        fallbacks=[
            CommandHandler('stop', stop_nested)
        ],

        map_to_parent={
            # Return to top level menu
            END: SELECTING_ACTION,
            # End conversation alltogether
            STOPPING: END,
        }
    )

    # Set up top level ConversationHandler (selecting action)
    # Because the states of the third level conversation map to the ones of the second level
    # conversation, we need to make sure the top level conversation can also handle them
    selection_handlers = [
        choose_building_convo,
        event_handling_convo
    ]

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],

        states={
            SELECTING_ACTION: selection_handlers,
            HANDLING_EVENT: selection_handlers,
            STOPPING: [CommandHandler('start', start)],
        },

        fallbacks=[
            CommandHandler('stop', stop)],
    )

    dp.add_handler(conv_handler)
    dp.add_handler(CommandHandler("help", help))

    #run locally
    #updater.start_polling()

    # log all errors
    dp.add_error_handler(error)
    updater.start_webhook(listen="0.0.0.0",
                          port=int(PORT),
                          url_path=TOKEN)
    updater.bot.setWebhook('https://student-saversbot.herokuapp.com/' + TOKEN)


if __name__ == '__main__':
    main()
