import mysql.connector
import os
from flask import Flask, render_template, request, url_for, flash, redirect,jsonify
from werkzeug.exceptions import abort
from werkzeug.utils import secure_filename
from threading import Thread 
import jwt 
import json 
import requests 
from datetime import datetime, timedelta
from flask_login import  UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_mail import Message, Mail 
#from flask_ckeditor import CKEditor
#import markdown
newapp = Flask(__name__)
newapp.config['DEBUG'] = True
newapp.config['UPLOAD_FOLDER'] = 'uploads'
newapp.config['MAIL_SERVER'] = 'smtp.iitd.ac.in'
newapp.config['MAIL_PORT'] = 25
newapp.config['MAIL_USE_TLS'] = True
newapp.config['MAIL_USE_SSL'] = False 
newapp.config['MAIL_DEBUG'] =True
newapp.config['MAIL_USERNAME'] = "cs1210566@iitd.ac.in"
newapp.config['MAIL_DEFAULT_SENDER'] = "cs1210566@iitd.ac.in"
newapp.config['MAIL_PASSWORD'] = "efd3f952"
mail = Mail(newapp)
newapp.config['SECRET_KEY'] = 'sql@Prism1920'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in set(['png','jpg','jpeg','gif'])

def get_db_connection():
    mydb = mysql.connector.connect(
	    #  port = 4545,
        host = "localhost",
        user = "root",
        password = "Pran@2010",
	    auth_plugin = "mysql_native_password",
        database = "BugSearch"
    )
    return mydb

my_db=get_db_connection()

login_manager = LoginManager()
login_manager.init_app(newapp)
login_manager.login_view = 'login'
login_manager.id_attribute ='get_id'

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

class User(UserMixin):
    def __init__(self, **kwargs):
        self.user_id = kwargs.get('user_id')
        self.email_id = kwargs.get('email_id')
        self.passcode = kwargs.get('passcode')
        self.username = kwargs.get('username')
        self.creation_date = kwargs.get('creation_date')
        self.profile_image_url = kwargs.get('profile_image_url')
        self.reputation = kwargs.get('reputation')
        self.about = kwargs.get('about')
        self.badge = kwargs.get('badge')
        self.nfollowing = kwargs.get('nfollowing')
        self.nfollowers = kwargs.get('nfollowers')
        
    def get_id(self):
        return str(self.user_id)
    
    @staticmethod
    def find_by_email_id(email_id):
        my_db=get_db_connection()
        cursor = my_db.cursor(dictionary=True)
        query = "SELECT * FROM Users WHERE email_id = %s"
        cursor.execute(query, (email_id,))
        row = cursor.fetchone()
        my_db.close()
        if row:
            return User(**row)
        return None
    
    @staticmethod
    def find_by_username(username):
        my_db=get_db_connection()
        cursor = my_db.cursor(dictionary=True)
        query = "SELECT * FROM Users WHERE username = %s"
        cursor.execute(query, (username,))
        row = cursor.fetchone()
        
        my_db.close()
        if row:
            return User(**row)
        return None
    
    @staticmethod
    def get(user_id):
        my_db=get_db_connection()
        cursor = my_db.cursor(dictionary=True)
        query = "SELECT * FROM Users WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        row = cursor.fetchone()
        
        my_db.close()
        if row:
            return User(**row)
        return None

    @staticmethod
    def create(email_id, passcode, username):
        my_db=get_db_connection()
        cursor = my_db.cursor(dictionary=True)
        hashed_passcode=passcode
        query = "INSERT INTO Users (email_id, passcode, username) VALUES (%s, %s, %s)"
        cursor.execute(query, (email_id, hashed_passcode, username))
        my_db.commit()
        user_id=cursor.lastrowid
        query="SELECT * FROM Users WHERE user_id=%s"
        cursor.execute(query,(user_id,))
        row=cursor.fetchone()
        my_db.close()
        return User(**row)
    
    @staticmethod
    def update_profile(user,about,profile_image_url,tags):
        user_id=user.user_id
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="UPDATE Users SET about=%s,profile_image_url=%s WHERE user_id=%s"
        val=(about,profile_image_url,user.user_id)
        cursor.execute(query,val) 
        my_db.commit()
        cursor.execute("SELECT * FROM Users WHERE user_id=%s",(user.user_id,))
        row=cursor.fetchone()
        query='DELETE FROM Usertags WHERE user_id=%s'
        cursor.execute(query,(user.user_id,))
        my_db.commit()
        query = "INSERT INTO Usertags (tag_name, user_id) VALUES (%s, %s)"
        values = [(tag_name, user_id) for tag_name in tags]
        cursor = my_db.cursor()
        cursor.executemany(query, values)
        my_db.commit()
        my_db.close()
        return User(**row)
    
    @staticmethod
    def find_followers(user_id):
        my_db=get_db_connection()
        query = "SELECT follower_id FROM Followertags WHERE following_id = %s ORDER BY creation_date DESC"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(user_id,))
        fol_id=cursor.fetchall()
        u_list=[]
        my_db.close()
        for f_id in fol_id:
            u_list.append(User.get(f_id['follower_id']))
        return u_list

    @staticmethod
    def find_followings(user_id):
        my_db=get_db_connection()
        query = "SELECT following_id FROM Followertags WHERE follower_id = %s ORDER BY creation_date DESC"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(user_id,))
        foll_id=cursor.fetchall()
        u_list=[]
        my_db.close()
        for f_id in foll_id:
            u_list.append(User.get(f_id['following_id']))
        return u_list
    
    @staticmethod
    def get_reset_token(username):
        return jwt.encode({'reset_password': username, 'exp': datetime.utcnow() + timedelta(minutes = 30)}, key=newapp.config['SECRET_KEY'])

    @staticmethod
    def set_password(username,passcode):
        my_db=get_db_connection()
        cursor = my_db.cursor(dictionary=True)
        query = "UPDATE Users SET passcode = %s WHERE username = %s"
        cursor.execute(query, (passcode,username,))
        my_db.commit()
        my_db.close()
        user = User.find_by_username(username)
        if user.passcode == passcode: return 1
        else: return 0
        

    @staticmethod
    def find_allusers():
        my_db=get_db_connection()
        cursor = my_db.cursor(dictionary=True)
        query = "SELECT * FROM Users ORDER BY username ASC"
        cursor.execute(query)
        users=cursor.fetchall()
        u_list=[]
        for u in users:
            u_list.append(User(**u))
        return u_list


class Question():
    def __init__(self,**kwargs):
        self.question_id=kwargs.get('question_id')
        self.title=kwargs.get('title') 
        self.body=kwargs.get('body')
        self.answer_id=kwargs.get('answer_id') 
        self.user_id=kwargs.get('user_id') 
        self.score=kwargs.get('score') 
        self.creation_date=kwargs.get('creation_date') 
        self.comment_count=kwargs.get('comment_count') 
        self.answer_count=kwargs.get('answer_count') 
        self.upvotes=kwargs.get('upvotes') 
        self.downvotes=kwargs.get('downvotes')

    @staticmethod
    def find_by_keyword(keyword):
        my_db=get_db_connection()
        query = "SELECT * FROM Questions WHERE MATCH(title,body) AGAINST (%s IN NATURAL LANGUAGE MODE)"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query, (keyword,))
        questions=cursor.fetchall()
        my_db.close()
        q_list=[]
        for q in questions:
            q_list.append(Question(**q))
        return q_list

    @staticmethod
    def post_question(title,body,tags,user_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="INSERT INTO Questions (title,body,user_id) VALUES(%s,%s,%s)"
        cursor.execute(query,(title,body,user_id))
        my_db.commit()
        question_id=cursor.lastrowid
        query="SELECT * FROM Questions WHERE question_id=%s"
        cursor.execute(query,(question_id,))
        question=cursor.fetchone()
        query = "INSERT INTO Questiontags (tag_name, question_id) VALUES (%s, %s)"
        values = [(tag, question_id) for tag in tags]
        cursor = my_db.cursor()
        cursor.executemany(query, values)
        my_db.commit()
        my_db.close()
        return Question(**question)
        
    @staticmethod
    def delete_question_by_id(question_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="DELETE FROM Questions WHERE question_id=%s"
        cursor.execute(query,(question_id,))
        my_db.commit()
        my_db.close()
        return "successfully deleted" 
    
    @staticmethod
    def find_by_question_id(question_id):
        my_db=get_db_connection()
        query="SELECT * FROM Questions WHERE question_id=%s"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(question_id,))
        row=cursor.fetchone()
        my_db.close()
        if row:
            return Question(**row)
        return None

    @staticmethod
    def get_comments_by_question_id(question_id):
        my_db=get_db_connection()
        query = "SELECT * FROM Question_comments WHERE question_id = %s ORDER BY creation_date"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(question_id,))
        comments=cursor.fetchall()
        my_db.close()
        l_comments=[]
        for comment in comments:
            l_comments.append(Question_Comment(**comment))
        return l_comments
        
    @staticmethod
    def find_answers_by_question_id(question_id):
        my_db=get_db_connection()
        query = "SELECT * FROM Answers WHERE question_id = %s ORDER BY creation_date ASC"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(question_id,))
        answers=cursor.fetchall()
        my_db.close()
        l_answers=[]
        for answer in answers:
            l_answers.append(Answer(**answer))
        return l_answers
    
    @staticmethod
    def get_accepted_answer_of_question_id(question):
        my_db=get_db_connection()
        answer_id=question.answer_id
        query = "SELECT * FROM Answers WHERE answer_id = %s "
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(answer_id,))
        answer=cursor.fetchone()
        my_db.close()
        if answer:
            return Answer(**answer)
        return None
    
    @staticmethod
    def find_question_by_user_id(user_id):
        my_db=get_db_connection()
        query = "SELECT * FROM Questions WHERE user_id = %s ORDER BY creation_date DESC"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(user_id,))
        questions=cursor.fetchall()
        my_db.close()
        q_list=[]
        for q in questions:
            q_list.append(Question(**q))
        return q_list

    @staticmethod
    def find_trending_ques():
        my_db=get_db_connection()
        query = "SELECT * FROM Questions ORDER BY score DESC"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query)
        questions=cursor.fetchall()
        my_db.close()
        q_list=[]
        for q in questions:
            q_list.append(Question(**q))
        return q_list

    @staticmethod 
    def find_recent_ques():
        my_db=get_db_connection()
        query = "SELECT * FROM Questions ORDER BY creation_date DESC"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query)
        questions=cursor.fetchall()
        
        q_list=[]
        for q in questions:
            # query1 = "UPDATE Questions SET Answer_count = %s WHERE question_id = %s"
            # query2 = "SELECT * FROM Answers WHERE question_id = %s ORDER BY creation_date DESC"
            # cursor=my_db.cursor(dictionary=True)
            # cursor.execute(query2,(Question(**q).question_id,))
            # answers=cursor.fetchall()
            # cursor.execute(query1,(len(answers),Question(**q).question_id,))
            q_list.append(Question(**q))
        # my_db.commit()
        my_db.close()
        return q_list

class Answer():
    def __init__(self,**kwargs):
        self.question_id=kwargs.get('question_id') 
        self.body=kwargs.get('body')  
        self.answer_id=kwargs.get('answer_id')  
        self.user_id=kwargs.get('user_id')  
        self.score=kwargs.get('score')  
        self.creation_date=kwargs.get('creation_date')  
        self.comment_count=kwargs.get('comment_count')  
        self.upvotes=kwargs.get('upvotes')  
        self.downvotes=kwargs.get('downvotes') 
    @staticmethod
    def post_answer(user_id,question_id,body):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="INSERT INTO Answers (body,user_id,question_id) VALUES(%s,%s,%s)"
        cursor.execute(query,(body,user_id,question_id))
        answer_id=cursor.lastrowid
        my_db.commit()
        query = "UPDATE Questions SET answer_count = answer_count + 1 WHERE question_id = %s"
        cursor.execute(query, (question_id,))
        my_db.commit()
        my_db.close()
        if answer_id is None:
            return "failed", 400
        else:
            return "Successfully posted",200
    
    @staticmethod
    def find_by_answer_id(answer_id):
        my_db=get_db_connection()
        query="SELECT * FROM Answers WHERE answer_id=%s"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(answer_id,))
        row=cursor.fetchone()
        my_db.close()
        if row:
            return Answer(**row)
        return None
    
    @staticmethod
    def get_comments_by_answer_id(answer_id):
        my_db=get_db_connection()
        query = "SELECT * FROM Answer_comments WHERE answer_id = %s ORDER BY creation_date ASC"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(answer_id,))
        comments=cursor.fetchall()
        my_db.close()
        l_comments=[]
        for comment in comments:
            l_comments.append(Answer_Comment(**comment))
        return l_comments
    
    @staticmethod
    def delete_answer_by_id(answer_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="DELETE FROM Answers WHERE answer_id=%s"
        cursor.execute(query,(answer_id,))
        my_db.commit()
        my_db.close()
        return "successfully deleted"
    
    @staticmethod
    def find_answer_by_user_id(user_id):
        my_db=get_db_connection()
        query = "SELECT * FROM answers WHERE user_id = %s ORDER BY creation_date DESC"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(user_id,))
        answers=cursor.fetchall()
        my_db.close()
        a_list=[]
        for a in answers:
            a_list.append(Answer(**a))
        return a_list
    
    @staticmethod
    def find_ans_by_ques_id(question_id):
        my_db=get_db_connection()
        query = "SELECT * FROM Answers WHERE question_id = %s ORDER BY creation_date DESC"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(question_id,))
        answers=cursor.fetchall()
        my_db.close()
        a_list=[]
        for a in answers:
            a_list.append(Answer(**a))
        return a_list


class Question_Comment():
    def __init__(self,**kwargs):
        
        self.body=kwargs.get('body')
        
        self.creation_date=kwargs.get('creation_date')
        

    @staticmethod
    def post_qcomment(question_id,user_id,body):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="INSERT INTO Question_comments (body,user_id,question_id) VALUES(%s,%s,%s)"
        cursor.execute(query,(body,user_id,question_id))
        qcomment=cursor.fetchone()
        my_db.commit()
        query = "UPDATE Questions SET comment_count = comment_count + 1 WHERE question_id = %s"
        cursor.execute(query, (question_id,))
        my_db.commit()
        my_db.close()
        if qcomment is None:
            return "failed", 400
        else:
            return "Successfully posted",200 
    
    @staticmethod
    def find_qcomment_by_id(question_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT body FROM Question_comments WHERE question_id=%s ORDER BY CREATION_DATE DESC"
        cursor.execute(query,(question_id,))
        row =cursor.fetchall()
        return row
  
class Answer_Comment():

    def __init__(self,**kwargs):
        self.body=kwargs.get('body')
        self.creation_date=kwargs.get('creation_date')
        
    @staticmethod
    def post_acomment(answer_id,user_id,body):
            my_db=get_db_connection()
            cursor=my_db.cursor(dictionary=True)
            query="INSERT INTO Answer_comments (body,user_id,answer_id) VALUES(%s,%s,%s)"
            cursor.execute(query,(body,user_id,answer_id))
            acomment=cursor.fetchone()
            my_db.commit()
            query="UPDATE Answers  SET comment_count=comment_count+1 WHERE answer_id=%s"
            cursor.execute(query,(answer_id,))
            my_db.commit() 
            my_db.close()
            if acomment is None:
                return "failed", 400
            else:
                return "Successfully posted",200

    @staticmethod
    def find_acomment_by_id(answer_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT body FROM Answer_comments WHERE answer_id =%s ORDER BY creation_date DESC"
        cursor.execute(query,(answer_id,))
        row =cursor.fetchall()
        return row
        
class Tag():
    def __init__(self,**kwargs):
        self.tag_id=kwargs.get('tag_id')
        self.tag_name=kwargs.get('tag_name')
        self.about=kwargs.get('about')
        self.creation_date=kwargs.get('creation_date')

    @staticmethod
    def find_all_tags():
        my_db=get_db_connection()
        query="SELECT tag_name FROM Tags ORDER BY tag_name ASC;"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query)
        row=cursor.fetchall()
        my_db.close() 
        return row

    @staticmethod
    def tags_by_userIdnot(user_id):
        my_db = get_db_connection()
        query = """
            SELECT t.tag_name
            FROM Tags t
            LEFT JOIN Usertags u ON t.tag_name = u.tag_name AND u.user_id = %s
            WHERE u.tag_name IS NULL
            ORDER BY t.tag_name ASC;
        """
        cursor = my_db.cursor()
        cursor.execute(query, (user_id,))
        tags = cursor.fetchall()
        
        tag_list = [{'tag_name': tag[0]} for tag in tags]
        return tag_list

    @staticmethod
    def find_tags_by_question_id(question_id):
        my_db=get_db_connection()
        query="SELECT tag_name FROM Questiontags WHERE question_id= %s ;"
        cursor=my_db.cursor(dictionary=True)
        cursor.execute(query,(question_id,))
        tag_names=cursor.fetchall()        
        return tag_names
    
    @staticmethod
    def find_tags_by_user_id(user_id):
        my_db=get_db_connection()
        query="SELECT tag_name FROM Usertags WHERE user_id= %s ;"
        cursor=my_db.cursor()
        cursor.execute(query,(user_id,))
        tag_names=cursor.fetchall()
        return tag_names
    
class QVote:
    def __init__(self,**kwargs):
        self.vote_type=kwargs.get('vote_type')
        self.question_id=kwargs.get('question_id')
        self.user_id=kwargs.get('user_id')

    @staticmethod
    def Qfindvote(user_id,question_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT * FROM Question_votes WHERE user_id=%s AND question_id=%s"
        cursor.execute(query,(user_id,question_id))
        vote=cursor.fetchone()
        my_db.close()
        if(vote is None):
            return ("neutral")
        else:
            return vote['vote_type']
        
    @staticmethod
    def Qmanagereputation(question_id,points):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT user_id FROM Questions WHERE question_id=%s" 
        cursor.execute(query,(question_id,))
        user_id=cursor.fetchone()['user_id']
        query="UPDATE Users SET reputation=reputation+%s WHERE user_id=%s"
        cursor.execute(query,(points,user_id,))
        my_db.commit()
        my_db.close()
        
    @staticmethod
    def Qupdatevote(user_id,question_id,voting):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT vote_type FROM Question_votes WHERE user_id=%s AND question_id=%s"
        cursor.execute(query,(user_id,question_id))
        vote=cursor.fetchone()
        if(vote is None):
            if(voting=='up'):
                query="INSERT INTO Question_votes (user_id,question_id,vote_type) values(%s,%s,%s)"
                cursor.execute(query,(user_id,question_id,'upvote'))
                my_db.commit()
                query = "UPDATE Questions SET upvotes = upvotes + 1,score=score+1 WHERE question_id = %s"
                cursor.execute(query, (question_id,))
                my_db.commit()
                my_db.close()
                QVote.Qmanagereputation(question_id,points=5)
                return 'upvote'
            else:
                query="INSERT INTO Question_votes (user_id,question_id,vote_type) values(%s,%s,%s)"
                cursor.execute(query,(user_id,question_id,'downvote'))
                my_db.commit()
                query = "UPDATE Questions SET downvotes = downvotes + 1,score=score-1 WHERE question_id = %s"
                cursor.execute(query, (question_id,))
                my_db.commit()
                my_db.close()
                QVote.Qmanagereputation(question_id,points=-2)
                return 'downvote'
        elif (vote['vote_type']=='neutral'):
            if(voting=='up'):
                query = "UPDATE Question_votes SET vote_type = %s WHERE user_id = %s AND question_id = %s"
                cursor.execute(query, ('upvote', user_id, question_id))
                my_db.commit()
                query = "UPDATE Questions SET upvotes = upvotes + 1,score=score+1 WHERE question_id = %s"
                cursor.execute(query, (question_id,))
                my_db.commit()
                my_db.close()
                QVote.Qmanagereputation(question_id,points=5)
                return 'upvote'
            else:
                query = "UPDATE Question_votes SET vote_type = %s WHERE user_id = %s AND question_id = %s"
                cursor.execute(query, ('downvote', user_id, question_id))
                my_db.commit()
                query = "UPDATE Questions SET downvotes = downvotes + 1,score=score-1 WHERE question_id = %s"
                cursor.execute(query, (question_id,))
                my_db.commit()
                my_db.close()
                QVote.Qmanagereputation(question_id,points=-2)
                return 'downvote'
        elif (vote['vote_type']=='upvote'):
            if(voting=='up'):
                query = "UPDATE Question_votes SET vote_type = %s WHERE user_id = %s AND question_id = %s"
                cursor.execute(query, ('neutral', user_id, question_id))
                my_db.commit()
                query = "UPDATE Questions SET upvotes = upvotes - 1,score=score-1 WHERE question_id = %s"
                cursor.execute(query, (question_id,))
                my_db.commit()
                my_db.close()
                QVote.Qmanagereputation(question_id,points=-5)
                return 'neutral'
            else:
                query = "UPDATE Question_votes SET vote_type = %s WHERE user_id = %s AND question_id = %s"
                cursor.execute(query, ('downvote', user_id, question_id))
                my_db.commit()
                query = "UPDATE Questions SET upvotes = upvotes - 1,downvotes=downvotes +1,score=score-2 WHERE question_id = %s"
                cursor.execute(query, (question_id,))
                my_db.commit()
                my_db.close()
                QVote.Qmanagereputation(question_id,points=-7)
                return 'downvote'
        else:
            if(voting=='down'):
                query = "UPDATE Question_votes SET vote_type = %s WHERE user_id = %s AND question_id = %s"
                cursor.execute(query, ('neutral', user_id, question_id))
                my_db.commit()
                query = "UPDATE Questions SET downvotes = downvotes - 1,score=score+1  WHERE question_id = %s"
                cursor.execute(query, (question_id,))
                my_db.commit()
                my_db.close()
                QVote.Qmanagereputation(question_id,points=2)
                return 'neutral'
            else:
                query = "UPDATE Question_votes SET vote_type = %s WHERE user_id = %s AND question_id = %s"
                cursor.execute(query, ('upvote', user_id, question_id))
                my_db.commit()
                query = "UPDATE Questions SET upvotes = upvotes + 1,downvotes=downvotes-1,score=score+2 WHERE question_id = %s"
                cursor.execute(query, (question_id,))
                my_db.commit()
                my_db.close()
                QVote.Qmanagereputation(question_id,points=7)
                return 'upvote'

class AVote:
    def __init__(self,**kwargs):
        self.vote_type=kwargs.get('vote_type')
        self.answer_id=kwargs.get('answer_id')
        self.user_id=kwargs.get('user_id')

    @staticmethod
    def Afindvote(user_id,answer_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT * FROM Answer_votes WHERE user_id=%s AND answer_id=%s"
        cursor.execute(query,(user_id,answer_id))
        vote=cursor.fetchone()
        my_db.close()
        if(vote is None):
            return ("neutral")
        else:
            return vote['vote_type']
        
    @staticmethod
    def Amanagereputation(answer_id,points):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT user_id FROM Answers WHERE answer_id=%s" 
        cursor.execute(query,(answer_id,))
        user_id=cursor.fetchone()['user_id']
        query="UPDATE Users SET reputation=reputation+%s WHERE user_id=%s"
        cursor.execute(query,(points,user_id,))
        my_db.commit()
        my_db.close()

    @staticmethod
    def Aupdatevote(user_id,answer_id,voting):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT vote_type FROM Answer_votes WHERE user_id=%s AND answer_id=%s"
        cursor.execute(query,(user_id,answer_id))
        vote=cursor.fetchone()
        if(vote is None):
            if(voting=='up'):
                query="INSERT INTO Answer_votes (user_id,answer_id,vote_type) values(%s,%s,%s)"
                cursor.execute(query,(user_id,answer_id,'upvote'))
                my_db.commit()
                query = "UPDATE Answers SET upvotes = upvotes + 1, score =score+1  WHERE answer_id = %s"
                cursor.execute(query, (answer_id,))
                my_db.commit()
                my_db.close()
                AVote.Amanagereputation(answer_id,points=5)
                return 'upvote'
            else:
                query="INSERT INTO Answer_votes (user_id,answer_id,vote_type) values(%s,%s,%s)"
                cursor.execute(query,(user_id,answer_id,'downvote'))
                my_db.commit()
                query = "UPDATE Answers SET downvotes = downvotes + 1, score=score-1 WHERE answer_id = %s"
                cursor.execute(query, (answer_id,))
                my_db.commit()
                my_db.close()
                AVote.Amanagereputation(answer_id,points=-2)
                return 'downvote'
        elif (vote['vote_type']=='neutral'):
            if(voting=='up'):
                query = "UPDATE Answer_votes SET vote_type = %s WHERE user_id = %s AND answer_id = %s"
                cursor.execute(query, ('upvote', user_id, answer_id))
                my_db.commit()
                query = "UPDATE Answers SET upvotes = upvotes + 1, score=score+1 WHERE answer_id = %s"
                cursor.execute(query, (answer_id,))
                my_db.commit()
                my_db.close()
                AVote.Amanagereputation(answer_id,points=5)
                return 'upvote'
            else:
                query = "UPDATE Answer_votes SET vote_type = %s WHERE user_id = %s AND answer_id = %s"
                cursor.execute(query, ('downvote', user_id, answer_id))
                my_db.commit()
                query = "UPDATE Answers SET downvotes = downvotes + 1,score=score-1 WHERE answer_id = %s"
                cursor.execute(query, (answer_id,))
                my_db.commit()
                my_db.close()
                AVote.Amanagereputation(answer_id,points=-2)
                return 'downvote'
        elif (vote['vote_type']=='upvote'):
            if(voting=='up'):
                query = "UPDATE Answer_votes SET vote_type = %s WHERE user_id = %s AND answer_id = %s"
                cursor.execute(query, ('neutral', user_id, answer_id))
                my_db.commit()
                query = "UPDATE Answers SET upvotes = upvotes - 1,score=score-1 WHERE answer_id = %s"
                cursor.execute(query, (answer_id,))
                my_db.commit()
                my_db.close()
                AVote.Amanagereputation(answer_id,points=-5)
                return 'neutral'
            else:
                query = "UPDATE Answer_votes SET vote_type = %s WHERE user_id = %s AND answer_id = %s"
                cursor.execute(query, ('downvote', user_id, answer_id))
                my_db.commit()
                query = "UPDATE Answers SET upvotes = upvotes - 1,downvotes=downvotes-1,score=score-2 WHERE answer_id = %s"
                cursor.execute(query, (answer_id,))
                my_db.commit()
                my_db.close()
                AVote.Amanagereputation(answer_id,points=-7)
                return 'downvote'
        else:
            if(voting=='down'):
                query = "UPDATE Answer_votes SET vote_type = %s WHERE user_id = %s AND answer_id = %s"
                cursor.execute(query, ('neutral', user_id, answer_id))
                my_db.commit()
                query = "UPDATE Answers SET downvotes = downvotes - 1, score=score+1  WHERE answer_id = %s"
                cursor.execute(query, (answer_id,))
                my_db.commit()
                my_db.close()
                AVote.Amanagereputation(answer_id,points=2)
                return 'neutral'
            else:
                query = "UPDATE Answer_votes SET vote_type = %s WHERE user_id = %s AND answer_id = %s"
                cursor.execute(query, ('upvote', user_id, answer_id))
                my_db.commit()
                query = "UPDATE Answers SET upvotes = upvotes + 1,downvotes = downvotes - 1, score=score+2 WHERE answer_id = %s"
                cursor.execute(query, (answer_id,))
                my_db.commit()
                my_db.close()
                AVote.Amanagereputation(answer_id,points=7)
                return 'upvote'
        
class QBookmark:
    def __init__(self,**kwargs):
        self.creation_date=kwargs.get('creation_date')
        self.question_id=kwargs.get('question_id')
        self.user_id=kwargs.get('user_id')

    @staticmethod
    def Qfindbookmark(user_id,question_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT * FROM Question_bookmarks WHERE user_id=%s AND question_id=%s"
        cursor.execute(query,(user_id,question_id))
        vote=cursor.fetchone()
        if(vote is None):
            return ('no')
        else:
            return ('yes')
        
    @staticmethod
    def Qupdatebookmark(user_id,question_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT * FROM Question_bookmarks WHERE user_id=%s AND question_id=%s"
        cursor.execute(query,(user_id,question_id))
        bookmark=cursor.fetchone()        
        if bookmark is None:
            query="INSERT INTO Question_bookmarks (user_id,question_id) values(%s,%s)"
            cursor.execute(query,(user_id,question_id))
            my_db.commit()
            my_db.close()
            return ({"bookmark":"yes"})
        else:
            query="DELETE FROM Question_bookmarks WHERE user_id=%s AND question_id=%s"
            cursor.execute(query,(user_id,question_id))
            my_db.commit()
            my_db.close()
            return ({"bookmark":"no"})
    
    @staticmethod
    def Qfindmarked(user_id):    
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query = "SELECT question_id FROM Question_bookmarks WHERE user_id = %s ORDER BY creation_date DESC"
        cursor.execute(query,(user_id,))
        l_qid=cursor.fetchall()
        q_list=[]
        for id in l_qid:
            question=Question.find_by_question_id(id['question_id']) 
            q_list.append(question)
        return q_list

class ABookmark:
    def __init__(self,**kwargs):
        self.creation_time=kwargs.get('vote_type')
        self.answer_id=kwargs.get('answer_id')
        self.user_id=kwargs.get('user_id')

    @staticmethod
    def Afindbookmark(user_id,answer_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT * FROM Answer_bookmarks WHERE user_id=%s AND answer_id=%s"
        cursor.execute(query,(user_id,answer_id))
        vote=cursor.fetchone()
        my_db.close()
        if(vote is None):
            return ("no")
        else:
            return ('yes')
    
    @staticmethod
    def Aupdatebookmark(user_id,answer_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query="SELECT * FROM Answer_bookmarks WHERE user_id=%s AND answer_id=%s"
        cursor.execute(query,(user_id,answer_id))
        bookmark=cursor.fetchone()
        if bookmark is None:
            query="INSERT INTO Answer_bookmarks (user_id,answer_id) values(%s,%s)"
            cursor.execute(query,(user_id,answer_id))
            my_db.commit()
            my_db.close()
            return ({"bookmark":"yes"})
        else:
            query="DELETE FROM Answer_bookmarks WHERE user_id=%s AND answer_id=%s"
            cursor.execute(query,(user_id,answer_id))
            my_db.commit()
            my_db.close()
            return ({"bookmark":"no"})
        
    @staticmethod
    def Afindmarked(user_id):
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query = "SELECT answer_id FROM Answer_bookmarks WHERE user_id = %s ORDER BY creation_date DESC "
        cursor.execute(query,(user_id,))
        l_qid=cursor.fetchall()
        q_list=[]
        for id in l_qid:
            answer=Answer.find_by_answer_id(id['answer_id']) 
            q_list.append(answer)
        return q_list

@staticmethod
def find_questions_by_tag(tag_name):
    my_db=get_db_connection()
    query="SELECT question_id FROM Questiontags WHERE tag_name= %s ;"
    cursor=my_db.cursor()
    cursor.execute(query,(tag_name,))
    ques=cursor.fetchall()
    my_db.close() 
    q_list = []
    for ques_id in ques:
        q_list.append(Question.find_by_question_id(ques_id[0]))
    return q_list

def find_recommend_ques(user):
    my_db=get_db_connection()
    query="SELECT tag_name FROM Usertags WHERE user_id= %s ;"
    cursor=my_db.cursor()
    cursor.execute(query,(user.user_id,))
    user_tags=cursor.fetchall()
        # query = "SELECT * FROM Questions ORDER BY upvotes DESC"
        # cursor.execute(query)
        # questions=cursor.fetchall()
    my_db.close()
    q_list=[]
    for t in user_tags:
        q_list = q_list + find_questions_by_tag(t[0])
    return [*set(q_list)]

@login_required
@newapp.route('/users/user_home',methods=["GET",])
def user_home():
    q_list = Question.find_recent_ques()
    return render_template('user_home.html',user=current_user,q_list=q_list)

@login_required
@newapp.route('/logout',methods=['GET',])
def logout():
    logout_user()
    return redirect(url_for('userlogin'))

@login_required
@newapp.route('/users/all_users',methods=["GET",])
def all_users():    
    alluser_list=User.find_allusers()
    user_id=current_user.user_id
    u_list=[]
    my_db=get_db_connection()
    cursor=my_db.cursor(dictionary=True)
    query='SELECT * FROM Followertags WHERE follower_id = %s AND following_id=%s ' 
    for user in alluser_list:
        cursor.execute(query,(user_id,user.user_id))
        row=cursor.fetchone()
        if row is None:
            user.fstatus='follow'
        else:
            user.fstatus='unfollow'
        u_list.append(user)
    return render_template('all_users.html',user=current_user,u_list=u_list)

@login_required
@newapp.route("/users/badges",methods=["GET",])
def badges():
    return render_template('badges.html',user=current_user)

@login_required
@newapp.route('/users/bookmarks',methods=['GET',])
def bookmarks():
    q_list=QBookmark.Qfindmarked(user_id=current_user.user_id)
    a_list=ABookmark.Afindmarked(user_id=current_user.user_id)
    return render_template('bookmarks.html',user=current_user,q_list=q_list,a_list=a_list)

@login_required
@newapp.route("/users/complete_your_profile",methods=["GET",'POST'])
def complete_your_profile():
    if request.method=='POST':
        profile_img = request.files['profile_img']
        if profile_img:
            if not allowed_file(profile_img.filename):
                flash('Allowed image types are png, jpg, jpeg, gif.')
                return render_template("complete_your_profile.html",user=current_user, tag_list=Tag.tags_by_userIdnot(current_user.user_id))
            else:
                filename = secure_filename(profile_img.filename)
                profile_img.save(os.path.join('static',newapp.config['UPLOAD_FOLDER'],filename))
                profile_img_url = newapp.config['UPLOAD_FOLDER'] + '/' + filename
                about=request.form['about']
                tags=request.form.getlist('tags[]')
                user=User.update_profile(user=current_user,profile_image_url  = profile_img_url,tags=tags,about=about)
        else:
            profile_img_url = 'assets/images/default.jpg'
            about=request.form['about']
            tags=request.form.getlist('tags[]')
            user=User.update_profile(user=current_user,profile_image_url  = profile_img_url,tags=tags,about=about)
        return redirect(url_for('user_home',user=user))
    return render_template("complete_your_profile.html",user=current_user,tag_list=Tag.tags_by_userIdnot(current_user.user_id))

@login_required
@newapp.route('/users/dashboard', methods=['GET',])
def dashboard():
    tags=Tag.find_tags_by_user_id(current_user.user_id)
    return render_template("dashboard.html",user=current_user,tags=tags, follower=len(User.find_followers(current_user.user_id)), following=len(User.find_followings(current_user.user_id)))

@login_required
@newapp.route("/users/followers", methods=["GET",])
def followers():
    return render_template("followers.html",user=current_user,follower_list=User.find_followers(current_user.user_id))

@login_required
@newapp.route("/users/following", methods=["GET",])
def following():
    return render_template("following.html",user=current_user,following_list=User.find_followings(current_user.user_id))

@login_required
@newapp.route('/users/help_with_login',methods=['GET',])
def help_with_login():
    return render_template('help_with_login.html',user=current_user)

@login_required
@newapp.route('/users/questions',methods=['GET','POST'])
def post_question():
    if request.method=='POST':
        title=request.form['title']
        body=request.form['body']
        selected_tags = request.form.getlist('tags[]')
        question_id=Question.post_question(title=title, body=body,tags=selected_tags, user_id=current_user.user_id)
        if question_id:
            return redirect(url_for('posted_questions'))
    return render_template('post_question.html',user=current_user,tag_list=Tag.find_all_tags())

@login_required
@newapp.route('/users/questions/<int:question_id>',methods=["GET",])
def find_question(question_id):
    question=Question.find_by_question_id(question_id=question_id)
    list_ans=Answer.find_ans_by_ques_id(question_id)
    # question.answer_count=len(list_ans)
    id=current_user.user_id
    question.vote_type=QVote.Qfindvote(user_id=id,question_id=question.question_id)
    question.bookmark=QBookmark.Qfindbookmark(user_id=current_user.user_id,question_id=question.question_id)
    # qbody = markdown.markdown(question.body)
    l_ans=[]
    for ans in list_ans:
        ans.vote_type=AVote.Afindvote(user_id=id,answer_id=ans.answer_id)
        ans.bookmark=ABookmark.Afindbookmark(user_id=id,answer_id=ans.answer_id)
        l_ans.append(ans)
    return render_template('present_question.html',user=current_user,question=question,l_tags=Tag.find_tags_by_question_id(question_id),l_ans=l_ans)

@login_required
@newapp.route('/users/questions/<int:question_id>/answers',methods=['GET','POST'])
def post_answer(question_id):
    if request.method=="POST":
        body=request.form['body']
        answer=Answer.post_answer(user_id=current_user.user_id,body=body,question_id=question_id)
        return redirect(url_for('find_question',question_id=question_id))
    return render_template('post_answer.html',question_id=question_id,user=current_user)

@login_required
@newapp.route('/users/questions/<int:question_id>/answers/<int:answer_id>/comments',methods=['GET','POST'])
def post_answer_comment(question_id,answer_id):
    if request.method=="POST":
        body=request.form['body']
        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYzlhMzI4NjQtNjdiZS00NGE4LThhNTYtNzdmNGFkY2I5OWE1IiwidHlwZSI6ImFwaV90b2tlbiJ9.xWWB4F4usgqj5_HQ-kPG34qKsFuaWheeOBWCCSCELMk"}
        url ="https://api.edenai.run/v2/text/moderation"
        payload={"providers": "microsoft", "language": "en", "text": body}
        response = requests.post(url, json=payload, headers=headers)
        result = json.loads(response.text)
        if result['microsoft']['nsfw_likelihood'] >= 5:
            flash("Please don't post abusive content!")
            return redirect(url_for('post_question_comment',question_id=question_id))            
        if not body:
            flash('Content is required.')
            return redirect(url_for('post_question_comment',question_id=question_id))
        else:
            id=current_user.user_id
            Answer_Comment.post_acomment(user_id=id,body=body,answer_id=answer_id)
            return redirect(url_for('find_question',question_id=question_id)) 
    return render_template('post_acomment.html',answer_id=answer_id,question_id=question_id)
    
@login_required
@newapp.route('/users/questions/<int:question_id>/comments',methods=['GET','POST'])
def post_question_comment(question_id):
    if request.method=="POST":
        body=request.form['body']
        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYzlhMzI4NjQtNjdiZS00NGE4LThhNTYtNzdmNGFkY2I5OWE1IiwidHlwZSI6ImFwaV90b2tlbiJ9.xWWB4F4usgqj5_HQ-kPG34qKsFuaWheeOBWCCSCELMk"}
        url ="https://api.edenai.run/v2/text/moderation"
        payload={"providers": "microsoft", "language": "en", "text": body}
        response = requests.post(url, json=payload, headers=headers)
        result = json.loads(response.text)
        if result['microsoft']['nsfw_likelihood'] >= 5:
            flash("Please don't post abusive content!")
            return redirect(url_for('post_question_comment',question_id=question_id))
        if not body:
            flash('Content is required.')
            return redirect(url_for('post_question_comment',question_id=question_id))
        else:
            id=current_user.user_id
            Question_Comment.post_qcomment(user_id=id,body=body,question_id=question_id)
            return redirect(url_for('find_question',question_id=question_id))
    return render_template('post_qcomment.html',question_id=question_id) 
      
@login_required
@newapp.route("/users/posted_questions",methods=["GET","POST","DELETE"])
def posted_questions():
    id=current_user.user_id
    q_list=Question.find_question_by_user_id(user_id=id)
    return render_template('posted_questions.html',q_list=Question.find_question_by_user_id(user_id=id),user=current_user)


@login_required
@newapp.route('/users/recommendations',methods=['GET',])
def recommendations():
    q_list=find_recommend_ques(current_user)
    return render_template('recommendations.html',user=current_user,q_list=q_list)

@login_required
@newapp.route('/users/tags',methods=['GET',])
def tags_login():
    return render_template('tag_login.html',user=current_user)

@login_required
@newapp.route('/users/trending',methods=['GET',])
def trending():
    q_list=Question.find_trending_ques()
    return render_template('trending.html',user=current_user,q_list=q_list)

@login_required
@newapp.route('/users/search',methods=['POST',])
def search_login():
    keyword = request.form['keyword']
    q_list = Question.find_by_keyword(keyword) 
    return render_template('search_with_login.html',user=current_user,q_list=q_list,keyword=keyword)

@login_required
@newapp.route('/users/<string:username>',methods=['GET',])
def view_user(username):
    user = User.find_by_username(username)
    tags = Tag.find_tags_by_user_id(user.user_id)
    return render_template('user.html',user=user,tags=tags, follower=len(User.find_followers(user.user_id)), following=len(User.find_followings(user.user_id)))


@newapp.route('/signup', methods=('GET', 'POST'))
def signup():
    if(current_user.is_authenticated):
        return redirect(url_for('user_home'))
    elif request.method == 'POST':
        email_id = request.form['email_id']
        username = request.form['username']
        passcode = request.form['passcode']
        if (User.find_by_email_id(email_id)) is not None :
            flash('This email_id address is already registered, please login!')
            return render_template('signup.html')
        elif (User.find_by_username(username)) is not None :
            flash('Username already exists please enter other username!')
            return render_template('signup.html')
        else:
            user=User.create(username=username,email_id=email_id,passcode=passcode)
            login_user(user)
            return redirect(url_for('complete_your_profile'))
    return render_template('signup.html')

@newapp.route("/login",methods=["GET","POST"])
def userlogin():
    if(current_user.is_authenticated):
        return redirect(url_for('user_home'))
    elif (request.method=="POST"):
        username=request.form["username"]
        passcode=request.form["passcode"]
        remember = True if request.form.get('remember') else False
        user=User.find_by_username(username=username)
        if (user is None):
            flash("Incorrect username!")
            return render_template('login.html')
        elif (passcode!=user.passcode):
            flash("Incorrect password!")
            return render_template('login.html')
        else:
            login_user(user,remember=remember) 
            return redirect(url_for('user_home'))
    return render_template("login.html")

@newapp.route('/help',methods=["GET",])
def help():
    if(current_user.is_authenticated):
        return render_template("help_with_login.html")
    return render_template("help.html")
            
@newapp.route('/tags',methods=['GET',])
def tags():
    return render_template('tags.html')

def send_email(newapp, msg):
    with newapp.app_context():
        mail.send(msg)
        
@newapp.route("/forgot_password",methods=["GET","POST"])
def forgot_password():  
    if request.method=="POST":
        username = request.form['username']
        email_id = request.form['email_id']
        user = User.find_by_email_id(email_id)
        if (user!=None and User.find_by_username(username)==user):
            token = user.get_reset_token(username)
            msg=Message()
            msg.subject = "Password Recovery Mail"
            msg.recipients = [email_id]    
            url = request.host_url + url_for('reset_password',username=username,token=token)
            msg.html = render_template('reset_password_mail.html',url=url)
            Thread(target=send_email, args=(newapp,msg)).start()
            flash('email successfully sent!')
        else:
            flash('user does not exist!')
        render_template('password_reset_1.html')
    return render_template('password_reset_1.html')

@newapp.route("/reset_password/<string:username>/<string:token>",methods=["GET",'POST'])
def reset_password(username, token):
    if request.method=="POST":
        password1 = request.form['password1']
        password2 = request.form['password2']
        if (password1!=password2):
            flash("Passwords do not match!")
        else:
            reset = User.set_password(username,password1)
            if reset==1: flash("Password reset successfully!")
            else: flash("Something went wrong :(")
    return render_template('password_reset_2.html', username=username, token=token)

@newapp.route('/search',methods=["POST"])
def search_without_login():
    keyword = request.form['keyword']
    q_list = Question.find_by_keyword(keyword) 
    return render_template('search_without_login.html',q_list=q_list,keyword=keyword)

@newapp.route('/',methods=["GET","POST"])
def homepage():
    if request.method=="POST":
        searchKeyword = request.form['keyword']
        return redirect(url_for('search_without_login' ,keyword=searchKeyword))

    return render_template('index.html')

@login_required
@newapp.route('/checking',methods=['GET','POST'])
def handlechecking():
    return render_template('check.html')

@login_required
@newapp.route('/vote_bookmark_state', methods=['GET', 'POST'])
def Qloadvote():
    if request.method == 'POST':        
        data = request.get_json()
        post_id = data.get('post_id')
        post_type=data.get('post_type')
        user_id=current_user.user_id
        if(post_type=='question'):
            votetype=QVote.Qfindvote(user_id=user_id, question_id=post_id)
            bookmark=QBookmark.Qfindbookmark(user_id=user_id,question_id=post_id)
        else:
            votetype=AVote.Afindvote(user_id=user_id, answer_id=post_id)
            bookmark=ABookmark.Afindbookmark(user_id=user_id,answer_id=post_id) 
        return jsonify({"votetype":votetype,"bookmark":bookmark})
    
@login_required
@newapp.route('/updatevote', methods=['GET', 'POST'])
def updatevote():
    if request.method == 'POST':
        data = request.get_json()
        post_id = data.get('post_id')
        user_id = current_user.user_id
        vote_type=data.get('vote_type')
        post_type=data.get('post_type')
        if(post_type=='question'):
            vote=QVote.Qupdatevote(user_id=user_id,question_id=post_id,voting=vote_type)
            ObQ=Question.find_by_question_id(question_id=post_id)
            score=(ObQ.score)
            upvotes=ObQ.upvotes
            downvotes=ObQ.downvotes
        else:
            vote=AVote.Aupdatevote(user_id=user_id,answer_id=post_id,voting=vote_type)
            ObQ=Answer.find_by_answer_id(answer_id=post_id)
            score=(ObQ.score)
            upvotes=ObQ.upvotes
            downvotes=ObQ.downvotes
        return jsonify({"vote_type":vote,"upvotes":upvotes,"downvotes":downvotes,"score":score})

@login_required
@newapp.route('/updatebookmark',methods=['GET','POST'])
def udpatebookmark():
    if request.method=='POST':
        data=request.get_json()
        post_id=data.get('post_id')
        post_type=data.get('post_type')
        user_id=current_user.user_id
        if(post_type=='answer'):
            B=ABookmark.Aupdatebookmark(user_id=user_id,answer_id=post_id)
        else:
            B=QBookmark.Qupdatebookmark(user_id=user_id,question_id=post_id)
        return jsonify({"bookmark":B['bookmark']})

@login_required
@newapp.route('/getcomments',methods=['GET','POST'])
def getcomments():
    if request.method=='POST':
        data=request.get_json()
        post_id=data.get('post_id')
        post_type=data.get('post_type')
        if(post_type=='answer'):
            ac_list=Answer_Comment.find_acomment_by_id(answer_id=post_id)
            return jsonify(ac_list)
        else: 
            qc_list=Question_Comment.find_qcomment_by_id(question_id=post_id)
            return jsonify(qc_list) 
    else:
        return jsonify({'body':'my name is raja'})

@login_required
@newapp.route('/updatefollow',methods=['GET','POST'])
def udpatefollow():
    if request.method=='POST':
        data=request.get_json()
        id=data.get('user_id')
        user_id=current_user.user_id
        my_db=get_db_connection()
        cursor=my_db.cursor(dictionary=True)
        query='SELECT * FROM Followertags WHERE follower_id = %s AND following_id=%s ' 
        cursor.execute(query,(user_id,id))
        row=cursor.fetchone()
        if(row is None):
            query="INSERT INTO Followertags (follower_id,following_id) VALUES(%s,%s)"
            cursor.execute(query,(user_id,id))
            my_db.commit()
            query='UPDATE Users SET nfollowing=nfollowing+1 WHERE user_id=%s'
            cursor.execute(query,(user_id,))
            my_db.commit()
            query='UPDATE Users SET nfollowers=nfollowers+1 WHERE user_id=%s'
            cursor.execute(query,(id,))
            my_db.commit()
            my_db.close()
            return jsonify({'fstatus':'follow'})
        else:
            query="DELETE FROM Followertags WHERE follower_id=%s AND following_id=%s"
            cursor.execute(query,(user_id,id))
            my_db.commit()
            query='UPDATE Users SET nfollowing=nfollowing-1 WHERE user_id=%s'
            cursor.execute(query,(user_id,))
            my_db.commit()
            query='UPDATE Users SET nfollowers=nfollowers-1 WHERE user_id=%s'
            cursor.execute(query,(id,))
            my_db.commit()
            my_db.close()
            return jsonify({'fstatus':'unfollow'})

if __name__=="__main__":
    newapp.run(debug=True)
