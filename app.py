{\rtf1\ansi\ansicpg1252\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx566\tx1133\tx1700\tx2267\tx2834\tx3401\tx3968\tx4535\tx5102\tx5669\tx6236\tx6803\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import streamlit as st\
from datetime import datetime, timedelta\
\
# Simulazione di una telecamera\
cameras = \{\
    "Cam_01": datetime.now() - timedelta(hours=5),\
    "Cam_02": datetime.now() - timedelta(hours=13),\
    "Cam_03": datetime.now() - timedelta(days=1),\
\}\
\
st.title("\uc0\u55357 \u56615  Pannello Amministratore - Stato Telecamere")\
\
for cam_name, last_time in cameras.items():\
    hours_passed = (datetime.now() - last_time).total_seconds() / 3600\
    color = "\uc0\u55357 \u57314 " if hours_passed < 12 else "\u55357 \u56628 "\
    st.write(f"\{color\} **\{cam_name\}** - Ultima foto: \{last_time.strftime('%Y-%m-%d %H:%M:%S')\} (\{int(hours_passed)\}h fa)")\
}