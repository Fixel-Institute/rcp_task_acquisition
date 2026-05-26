# -*- coding: utf-8 -*-
import sqlite3
import os
from pathlib import Path

from rcp_task_acquisition.utils.logger import get_logger
logger = get_logger("./models/ParticipantDatabase") 

class ParticipantDatabase():
    def __init__(self):
        self.connection = None
        self.cursor = None
    
    
    def connect(self, filepath, filename):
        db_path = Path(filepath)
        db_path.mkdir(parents=True, exist_ok=True)
        file = os.path.join(db_path, filename)
        self.connection = sqlite3.connect(file)
        self.cursor = self.connection.cursor()
        
        #if table doesn't exist, create it
        create_table = '''
        CREATE TABLE IF NOT EXISTS Participants (
            ParticipantId VARCHAR(255) PRIMARY KEY,
            LastName VARCHAR(255),
            FirstName VARCHAR(255),
            Age VARCHAR(255),
            Diagnosis VARCHAR(255)
            );
        '''
        self.cursor.execute(create_table)
        self.connection.commit()
    
    
    def get_all_rows(self):
        select = "SELECT * FROM Participants;"
        participants = self.cursor.execute(select).fetchall()
        return participants
        
    
    def get_display_list(self):
        select = "SELECT ParticipantId, FirstName, LastName FROM Participants;"
        participants = self.cursor.execute(select).fetchall()
        # self.connection.commit()
        return participants
        
    
    def remove_participant(self, participant_id):
        remove = f"DELETE FROM Participants WHERE ParticipantId = '{participant_id}';"    
        self.cursor.execute(remove)
        self.connection.commit()
        
    def get_participant(self, column, condition):
        select = (f"SELECT * FROM Participants WHERE {column} = {condition};" )
        participant = self.cursor.execute(select).fetchall()
        return participant
    
    
    def add_participant(self, participant_id, first_name, last_name, age, diagnosis):
        row_str = ""
        col_str= "ParticipantId"
        row_str+="'"+participant_id +"'"
        
        if first_name != "":
            row_str += ",'" + first_name + "'"
            col_str+= ",FirstName"
        if last_name != "":
            row_str += ",'" + last_name + "'"
            col_str+= ",LastName"
        if age != "":
            row_str+= ",'" + age + "'"
            col_str+= ",Age"
        if diagnosis != "":
            row_str+= ",'" + diagnosis +"'"
            col_str+=",Diagnosis"
            
        insert = f"INSERT INTO Participants ({col_str}) VALUES ({row_str});"
                 
        try:
            self.cursor.execute(insert)
            self.connection.commit()
            logger.info("sucessfully added row to DB")
            return True, participant_id
        except Exception as e:
            logger.info(f"error adding to db: {e}")
            return False, ""
    
    
    def close(self):
        self.cursor.close()
        self.connection.close()
        
        




    
    
