import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import time
from dotenv import load_dotenv
from supabase import create_client, Client

# 環境変数をロード
load_dotenv()

# Supabaseクライアントの初期化
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    st.error("Supabaseの設定が見つかりません。.envファイルを確認してください。")
    st.stop()

supabase: Client = create_client(supabase_url, supabase_key)

# 認証トークンを設定する関数
def set_auth_token(access_token, refresh_token=None):
    if refresh_token:
        supabase.auth.set_session(access_token, refresh_token)
    else:
        supabase.auth.set_session(access_token, access_token)

# ページ設定
st.set_page_config(
    page_title="学習サポートアプリ",
    page_icon="📚",
    layout="wide"
)

# タイマーのセッション状態を初期化
if 'timer_running' not in st.session_state:
    st.session_state.timer_running = False
if 'timer_paused' not in st.session_state:
    st.session_state.timer_paused = False
if 'timer_start_time' not in st.session_state:
    st.session_state.timer_start_time = None
if 'timer_elapsed' not in st.session_state:
    st.session_state.timer_elapsed = 0
if 'timer_subject' not in st.session_state:
    st.session_state.timer_subject = ""
if 'timer_stopped_for_input' not in st.session_state:
    st.session_state.timer_stopped_for_input = False
if 'timer_stopped_duration' not in st.session_state:
    st.session_state.timer_stopped_duration = 0

# ==================== 認証機能 ====================

def signup_page():
    st.title("📚 学習サポートアプリ - 新規登録")
    
    email = st.text_input("メールアドレス")
    password = st.text_input("パスワード", type="password")
    
    if st.button("登録"):
        try:
            response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            if response.user:
                st.session_state.user = response.user
                if response.session:
                    st.session_state.access_token = response.session.access_token
                    set_auth_token(response.session.access_token)
                st.session_state.page = "main"
                st.success("登録しました！")
                st.rerun()
            else:
                st.success("登録メールを送信しました。メールを確認してください。")
        except Exception as e:
            st.error(f"登録に失敗しました: {str(e)}")
    
    st.markdown("---")
    st.write("既にアカウントをお持ちですか？")
    if st.button("ログインページへ"):
        st.session_state.page = "login"
        st.rerun()

def login_page():
    st.title("📚 学習サポートアプリ - ログイン")
    
    email = st.text_input("メールアドレス")
    password = st.text_input("パスワード", type="password")
    
    if st.button("ログイン"):
        try:
            response = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            st.session_state.user = response.user
            st.session_state.access_token = response.session.access_token
            set_auth_token(response.session.access_token)
            st.session_state.page = "main"
            st.success("ログインしました！")
            st.rerun()
        except Exception as e:
            st.error(f"ログインに失敗しました: {str(e)}")
    
    st.markdown("---")
    st.write("アカウントをお持ちでないですか？")
    if st.button("新規登録ページへ"):
        st.session_state.page = "signup"
        st.rerun()

def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.page = "login"
    st.rerun()

# ==================== データ操作関数 ====================

def get_user_schedules(user_id):
    try:
        response = supabase.table("schedules").select("*").eq("user_id", user_id).execute()
        return response.data
    except Exception as e:
        st.error(f"スケジュールの取得に失敗しました: {str(e)}")
        return []

def add_schedule(user_id, schedule_data):
    try:
        schedule_data["user_id"] = user_id
        response = supabase.table("schedules").insert(schedule_data).execute()
        return response.data[0]
    except Exception as e:
        st.error(f"スケジュールの追加に失敗しました: {str(e)}")
        return None

def update_schedule(schedule_id, schedule_data):
    try:
        response = supabase.table("schedules").update(schedule_data).eq("id", schedule_id).execute()
        return response.data[0]
    except Exception as e:
        st.error(f"スケジュールの更新に失敗しました: {str(e)}")
        return None

def delete_schedule(schedule_id):
    try:
        supabase.table("schedules").delete().eq("id", schedule_id).execute()
        return True
    except Exception as e:
        st.error(f"スケジュールの削除に失敗しました: {str(e)}")
        return False

def get_user_sessions(user_id):
    try:
        response = supabase.table("sessions").select("*").eq("user_id", user_id).execute()
        return response.data
    except Exception as e:
        st.error(f"学習記録の取得に失敗しました: {str(e)}")
        return []

def add_session(user_id, session_data):
    try:
        session_data["user_id"] = user_id
        response = supabase.table("sessions").insert(session_data).execute()
        return response.data[0]
    except Exception as e:
        st.error(f"学習記録の追加に失敗しました: {str(e)}")
        return None

def delete_session(session_id):
    try:
        supabase.table("sessions").delete().eq("id", session_id).execute()
        return True
    except Exception as e:
        st.error(f"学習記録の削除に失敗しました: {str(e)}")
        return False

def get_user_goals(user_id):
    try:
        response = supabase.table("goals").select("*").eq("user_id", user_id).execute()
        if response.data:
            return response.data[0]
        else:
            # デフォルトの目標を作成
            return {"daily": 120, "weekly": 600}
    except Exception as e:
        st.error(f"目標の取得に失敗しました: {str(e)}")
        return {"daily": 120, "weekly": 600}

def update_or_create_goals(user_id, goals_data):
    try:
        existing = supabase.table("goals").select("*").eq("user_id", user_id).execute()
        if existing.data:
            # 更新
            response = supabase.table("goals").update(goals_data).eq("user_id", user_id).execute()
        else:
            # 新規作成
            goals_data["user_id"] = user_id
            response = supabase.table("goals").insert(goals_data).execute()
        return True
    except Exception as e:
        st.error(f"目標の更新に失敗しました: {str(e)}")
        return False

# ==================== メインアプリ ====================

def main_app():
    user = st.session_state.user
    
    # サイドバー
    st.sidebar.title(f"👤 {user.email}")
    if st.sidebar.button("ログアウト"):
        logout()
    
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "メニュー",
        ["📅 スケジュール管理", "⏱️ タイマー", "🎯 目標設定", "📊 ダッシュボード", "📈 タイムライン比較"]
    )
    
    # 5分前通知のチェック
    now = datetime.now()
    schedules = get_user_schedules(user.id)
    upcoming_schedules = []
    for schedule in schedules:
        if not schedule["completed"]:
            schedule_date = datetime.strptime(schedule["date"], "%Y-%m-%d").date()
            schedule_time = datetime.strptime(schedule["start_time"], "%H:%M:%S").time()
            schedule_datetime = datetime.combine(schedule_date, schedule_time)
            
            if schedule_date == date.today():
                time_diff = (schedule_datetime - now).total_seconds()
                if 0 < time_diff <= 300:
                    upcoming_schedules.append(schedule)
    
    if upcoming_schedules:
        for schedule in upcoming_schedules:
            st.warning(f"🔔 通知: {schedule['subject']}の勉強時間がもうすぐです！（{schedule['start_time']}開始）")
    
    # ==================== スケジュール管理 ====================
    if page == "📅 スケジュール管理":
        st.header("📅 学習スケジュール管理")
        
        st.subheader("新しいスケジュールを追加")
        with st.form("schedule_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                subject = st.text_input("科目名", placeholder="例: 数学")
            with col2:
                study_date = st.date_input("日付", datetime.now())
            with col3:
                start_time = st.time_input("開始時刻", datetime.now().replace(hour=9, minute=0))
            
            duration = st.number_input("勉強時間（分）", min_value=15, max_value=480, value=60, step=15)
            notes = st.text_area("メモ（任意）", placeholder="勉強する内容や目標など")
            
            submitted = st.form_submit_button("スケジュールを追加")
            if submitted and subject:
                new_schedule = {
                    "subject": subject,
                    "date": str(study_date),
                    "start_time": str(start_time),
                    "duration": duration,
                    "notes": notes,
                    "completed": False
                }
                add_schedule(user.id, new_schedule)
                st.success("スケジュールを追加しました！")
                st.rerun()
        
        st.subheader("スケジュール一覧")
        schedules = get_user_schedules(user.id)
        if schedules:
            schedules_df = pd.DataFrame(schedules)
            schedules_df['date'] = pd.to_datetime(schedules_df['date'])
            schedules_df = schedules_df.sort_values('date')
            
            # カレンダー風表示
            st.subheader("📅 カレンダービュー")
            calendar_date = st.date_input("表示する日付", datetime.now(), key="calendar_date")
            
            day_schedules = [
                s for s in schedules
                if datetime.strptime(s["date"], "%Y-%m-%d").date() == calendar_date
            ]
            
            if day_schedules:
                # 時間軸表示
                import plotly.graph_objects as go
                
                fig = go.Figure()
                
                # 科目名ごとにY軸の位置を計算
                unique_subjects = sorted(set(s["subject"] for s in day_schedules))
                subject_to_y = {subject: i for i, subject in enumerate(unique_subjects)}
                
                for schedule in day_schedules:
                    start_dt = datetime.combine(calendar_date, datetime.strptime(schedule["start_time"], "%H:%M:%S").time())
                    end_dt = start_dt + timedelta(minutes=schedule["duration"])
                    
                    color = 'green' if schedule["completed"] else 'blue'
                    opacity = 0.5 if schedule["completed"] else 0.8
                    
                    fig.add_trace(go.Scatter(
                        x=[start_dt, end_dt],
                        y=[subject_to_y[schedule['subject']], subject_to_y[schedule['subject']]],
                        mode='lines+markers',
                        line=dict(color=color, width=30),
                        opacity=opacity,
                        name=schedule['subject'],
                        showlegend=False,
                        hovertext=f"{schedule['subject']}<br>{schedule['start_time']} - {datetime.strptime(schedule['start_time'], '%H:%M:%S') + timedelta(minutes=schedule['duration']):%H:%M}",
                        hoverinfo='text'
                    ))
                
                fig.update_layout(
                    title=f"{calendar_date}のスケジュール",
                    xaxis_title="時間",
                    yaxis_title="科目",
                    yaxis=dict(
                        tickmode='array',
                        tickvals=list(subject_to_y.values()),
                        ticktext=list(subject_to_y.keys())
                    ),
                    height=300,
                    hovermode='closest'
                )
                
                fig.update_layout(
                    title=f"{calendar_date}のスケジュール",
                    xaxis_title="時間",
                    yaxis_title="科目",
                    height=300,
                    hovermode='closest'
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            # リスト表示
            st.subheader("📋 リスト表示")
            for idx, row in schedules_df.iterrows():
                with st.expander(f"{row['date'].strftime('%Y/%m/%d')} - {row['subject']} ({row['duration']}分)"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**開始時刻:** {row['start_time']}")
                        st.write(f"**メモ:** {row['notes'] if row['notes'] else 'なし'}")
                    with col2:
                        if st.button("完了", key=f"complete_{row['id']}"):
                            update_schedule(row['id'], {"completed": True})
                            st.rerun()
                        if st.button("削除", key=f"delete_{row['id']}"):
                            delete_schedule(row['id'])
                            st.rerun()
        else:
            st.info("スケジュールがまだありません。上のフォームから追加してください。")
    
    # ==================== タイマー ====================
    elif page == "⏱️ タイマー":
        st.header("⏱️ 学習タイマー")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # スケジュールから科目を取得
            schedules = get_user_schedules(user.id)
            subject_list = list(set(s["subject"] for s in schedules)) if schedules else []
            
            # ドロップダウンで科目を選択、または手動入力
            subject = st.selectbox(
                "科目名を選択",
                options=subject_list + ["新しい科目を入力"],
                index=len(subject_list) if st.session_state.timer_subject not in subject_list else subject_list.index(st.session_state.timer_subject)
            )
            
            if subject == "新しい科目を入力":
                subject = st.text_input("新しい科目名", value=st.session_state.timer_subject, placeholder="例: 数学")
        
        with col2:
            if not st.session_state.timer_running:
                if st.button("▶️ スタート", type="primary"):
                    if subject:
                        st.session_state.timer_running = True
                        st.session_state.timer_paused = False
                        st.session_state.timer_start_time = time.time()
                        st.session_state.timer_elapsed = 0
                        st.session_state.timer_subject = subject
                        st.rerun()
                    else:
                        st.error("科目名を入力してください")
            else:
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("⏸️ 一時停止"):
                        st.session_state.timer_paused = True
                        st.session_state.timer_elapsed += time.time() - st.session_state.timer_start_time
                        st.rerun()
                with col_btn2:
                    if st.button("⏹️ 停止"):
                        total_elapsed = st.session_state.timer_elapsed
                        if not st.session_state.timer_paused:
                            total_elapsed += time.time() - st.session_state.timer_start_time
                        
                        st.session_state.timer_stopped_for_input = True
                        st.session_state.timer_stopped_duration = total_elapsed
                        st.session_state.timer_running = False
                        st.session_state.timer_paused = False
                        st.session_state.timer_start_time = None
                        st.session_state.timer_elapsed = 0
                        st.rerun()
        
        if st.session_state.timer_running:
            if st.session_state.timer_paused:
                elapsed = st.session_state.timer_elapsed
                st.info(f"⏸️ 一時停止中 - 経過時間: {int(elapsed // 60):02d}:{int(elapsed % 60):02d}")
            else:
                elapsed = st.session_state.timer_elapsed + (time.time() - st.session_state.timer_start_time)
                
                st.markdown("---")
                st.subheader("⏱️ 勉強中")
                
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    hours = int(elapsed // 3600)
                    minutes = int((elapsed % 3600) // 60)
                    seconds = int(elapsed % 60)
                    
                    if hours > 0:
                        time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        time_str = f"{minutes:02d}:{seconds:02d}"
                    
                    st.markdown(f"<h1 style='text-align: center; font-size: 80px; color: #4CAF50;'>{time_str}</h1>", unsafe_allow_html=True)
                    
                    current_time = datetime.now().strftime("%H:%M:%S")
                    st.markdown(f"<h3 style='text-align: center; color: #666;'>現在時刻: {current_time}</h3>", unsafe_allow_html=True)
                    
                    st.markdown(f"<p style='text-align: center; font-size: 20px;'>科目: {st.session_state.timer_subject}</p>", unsafe_allow_html=True)
                
                time.sleep(1)
                st.rerun()
        
        if st.session_state.timer_stopped_for_input:
            st.markdown("---")
            st.subheader("📝 学習記録を入力")
            st.info(f"勉強時間: {int(st.session_state.timer_stopped_duration / 60)}分")
            
            with st.form("timer_record_form"):
                progress = st.slider("進捗（%）", 0, 100, 50)
                notes = st.text_area("メモ（任意）", placeholder="学んだことや感想など")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("保存"):
                        new_session = {
                            "subject": st.session_state.timer_subject,
                            "date": str(date.today()),
                            "start_time": datetime.fromtimestamp(time.time() - st.session_state.timer_stopped_duration).strftime("%H:%M:%S"),
                            "end_time": datetime.now().strftime("%H:%M:%S"),
                            "duration": int(st.session_state.timer_stopped_duration / 60),
                            "progress": progress,
                            "notes": notes if notes else "タイマーからの記録"
                        }
                        add_session(user.id, new_session)
                        
                        st.session_state.timer_stopped_for_input = False
                        st.session_state.timer_stopped_duration = 0
                        st.success(f"{st.session_state.timer_subject}の学習を記録しました！")
                        st.rerun()
                with col2:
                    if st.form_submit_button("キャンセル"):
                        st.session_state.timer_stopped_for_input = False
                        st.session_state.timer_stopped_duration = 0
                        st.info("記録をキャンセルしました")
                        st.rerun()
        
        st.markdown("---")
        
        st.subheader("手動で学習記録を追加")
        with st.form("manual_session_form"):
            col1, col2 = st.columns(2)
            with col1:
                # スケジュールから科目を取得
                schedules = get_user_schedules(user.id)
                subject_list = list(set(s["subject"] for s in schedules)) if schedules else []
                
                # ドロップダウンで科目を選択、または手動入力
                manual_subject = st.selectbox(
                    "科目名を選択",
                    options=subject_list + ["新しい科目を入力"],
                    key="manual_subject_select"
                )
                
                if manual_subject == "新しい科目を入力":
                    manual_subject = st.text_input("新しい科目名", placeholder="例: 英語", key="manual_subject_input")
            with col2:
                manual_date = st.date_input("日付", datetime.now())
            
            col3, col4 = st.columns(2)
            with col3:
                manual_start_time = st.time_input("開始時刻", datetime.now().replace(hour=9, minute=0))
            with col4:
                manual_duration = st.number_input("勉強時間（分）", min_value=1, max_value=480, value=60)
            
            manual_progress = st.slider("進捗（%）", 0, 100, 50)
            manual_notes = st.text_area("メモ（任意）", placeholder="学んだことや感想など")
            
            manual_submitted = st.form_submit_button("手動で記録する")
            if manual_submitted and manual_subject:
                start_datetime = datetime.combine(manual_date, manual_start_time)
                end_datetime = start_datetime + timedelta(minutes=manual_duration)
                
                new_session = {
                    "subject": manual_subject,
                    "date": str(manual_date),
                    "start_time": str(manual_start_time),
                    "end_time": end_datetime.strftime("%H:%M:%S"),
                    "duration": manual_duration,
                    "progress": manual_progress,
                    "notes": manual_notes
                }
                add_session(user.id, new_session)
                st.success("学習を記録しました！")
                st.rerun()
        
        st.markdown("---")
        
        st.subheader("学習記録一覧")
        sessions = get_user_sessions(user.id)
        if sessions:
            sessions_df = pd.DataFrame(sessions)
            sessions_df['date'] = pd.to_datetime(sessions_df['date'])
            sessions_df = sessions_df.sort_values('date', ascending=False)
            
            for idx, row in sessions_df.iterrows():
                with st.expander(f"{row['date'].strftime('%Y/%m/%d')} - {row['subject']} ({row['duration']}分)"):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if 'start_time' in row:
                            st.write(f"**開始時刻:** {row['start_time']}")
                        if 'end_time' in row:
                            st.write(f"**終了時刻:** {row['end_time']}")
                        st.write(f"**進捗:** {row['progress']}%")
                        st.write(f"**メモ:** {row['notes'] if row['notes'] else 'なし'}")
                    with col2:
                        if st.button("削除", key=f"delete_session_{row['id']}"):
                            delete_session(row['id'])
                            st.success("記録を削除しました")
                            st.rerun()
            
            total_minutes = sessions_df['duration'].sum()
            total_hours = total_minutes / 60
            st.metric("総学習時間", f"{total_hours:.1f}時間 ({total_minutes}分)")
        else:
            st.info("学習記録がまだありません。")
    
    # ==================== 目標設定 ====================
    elif page == "🎯 目標設定":
        st.header("🎯 学習目標設定")
        
        goals = get_user_goals(user.id)
        
        st.subheader("目標時間を設定")
        
        col1, col2 = st.columns(2)
        with col1:
            daily_goal = st.number_input(
                "1日の目標学習時間（分）",
                min_value=15,
                max_value=480,
                value=goals.get("daily", 120),
                step=15
            )
        with col2:
            weekly_goal = st.number_input(
                "1週間の目標学習時間（分）",
                min_value=60,
                max_value=1680,
                value=goals.get("weekly", 600),
                step=30
            )
        
        if st.button("目標を保存"):
            update_or_create_goals(user.id, {"daily": daily_goal, "weekly": weekly_goal})
            st.success("目標を保存しました！")
        
        st.markdown("---")
        
        st.subheader("現在の進捗")
        
        sessions = get_user_sessions(user.id)
        if sessions:
            sessions_df = pd.DataFrame(sessions)
            sessions_df['date'] = pd.to_datetime(sessions_df['date'])
            
            today = date.today()
            today_sessions = sessions_df[sessions_df['date'].dt.date == today]
            today_minutes = today_sessions['duration'].sum()
            
            week_start = today - timedelta(days=today.weekday())
            week_sessions = sessions_df[sessions_df['date'].dt.date >= week_start]
            week_minutes = week_sessions['duration'].sum()
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(
                    "今日の学習時間",
                    f"{today_minutes}分 / {daily_goal}分",
                    f"{today_minutes - daily_goal:+d}分"
                )
                daily_progress = min(today_minutes / daily_goal * 100, 100) if daily_goal > 0 else 0
                st.progress(daily_progress / 100)
                st.caption(f"達成率: {daily_progress:.1f}%")
            
            with col2:
                st.metric(
                    "今週の学習時間",
                    f"{week_minutes}分 / {weekly_goal}分",
                    f"{week_minutes - weekly_goal:+d}分"
                )
                weekly_progress = min(week_minutes / weekly_goal * 100, 100) if weekly_goal > 0 else 0
                st.progress(weekly_progress / 100)
                st.caption(f"達成率: {weekly_progress:.1f}%")
        else:
            st.info("学習記録がまだありません。まずは学習を記録してください。")
    
    # ==================== ダッシュボード ====================
    elif page == "📊 ダッシュボード":
        st.header("📊 学習ダッシュボード")
        
        # 今日の達成率サマリー
        st.subheader("📅 今日の達成率")
        
        schedules = get_user_schedules(user.id)
        sessions = get_user_sessions(user.id)
        
        today = date.today()
        
        # 今日の学習記録
        today_sessions = [
            s for s in sessions
            if datetime.strptime(s["date"], "%Y-%m-%d").date() == today
        ]
        
        # 進捗の平均
        if today_sessions:
            avg_progress = sum(s["progress"] for s in today_sessions) / len(today_sessions)
            st.metric("平均進捗率", f"{avg_progress:.1f}%")
            st.progress(avg_progress / 100)
            st.caption(f"{len(today_sessions)}件の記録")
        else:
            st.info("今日の学習記録はありません")
        
        # 予定 vs 実績
        today_schedules = [
            s for s in schedules
            if datetime.strptime(s["date"], "%Y-%m-%d").date() == today
        ]
        scheduled_minutes = sum(s["duration"] for s in today_schedules)
        actual_minutes = sum(s["duration"] for s in today_sessions)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("予定学習時間", f"{scheduled_minutes}分")
        with col2:
            st.metric("実績学習時間", f"{actual_minutes}分")
        with col3:
            diff = actual_minutes - scheduled_minutes
            st.metric("差分", f"{diff:+d}分")
        
        st.markdown("---")
        
        # 科目別統計
        st.subheader("科目別学習時間")
        if sessions:
            sessions_df = pd.DataFrame(sessions)
            sessions_df['date'] = pd.to_datetime(sessions_df['date'])
            
            subject_stats = sessions_df.groupby('subject')['duration'].sum().sort_values(ascending=False)
            
            col1, col2 = st.columns(2)
            with col1:
                st.bar_chart(subject_stats)
            with col2:
                st.dataframe(subject_stats.reset_index().rename(columns={'duration': '総学習時間（分）'}))
            
            st.subheader("日別学習時間")
            daily_stats = sessions_df.groupby(sessions_df['date'].dt.date)['duration'].sum()
            st.line_chart(daily_stats)
            
            st.subheader("最近の学習記録")
            recent_sessions = sessions_df.sort_values('date', ascending=False).head(5)
            recent_sessions['date'] = recent_sessions['date'].dt.strftime('%Y/%m/%d')
            st.dataframe(recent_sessions[['date', 'subject', 'duration', 'progress', 'notes']], use_container_width=True)
        else:
            st.info("学習記録がまだありません。まずは学習を記録してください。")
    
    # ==================== タイムライン比較 ====================
    elif page == "📈 タイムライン比較":
        st.header("📈 予定 vs 実績 タイムライン比較")
        
        selected_date = st.date_input("比較する日付", datetime.now())
        
        st.subheader("📅 時間軸ビュー")
        
        schedules = get_user_schedules(user.id)
        sessions = get_user_sessions(user.id)
        
        # 予定データを準備
        schedule_data = []
        if schedules:
            day_schedules = [
                s for s in schedules
                if datetime.strptime(s["date"], "%Y-%m-%d").date() == selected_date
            ]
            for schedule in day_schedules:
                start_dt = datetime.combine(selected_date, datetime.strptime(schedule["start_time"], "%H:%M:%S").time())
                end_dt = start_dt + timedelta(minutes=schedule["duration"])
                schedule_data.append({
                    "Task": f"📅 {schedule['subject']}",
                    "Start": start_dt,
                    "Finish": end_dt,
                    "Type": "予定",
                    "Completed": schedule["completed"]
                })
        
        # 実績データを準備
        session_data = []
        if sessions:
            day_sessions = [
                s for s in sessions
                if datetime.strptime(s["date"], "%Y-%m-%d").date() == selected_date
            ]
            for session in day_sessions:
                if 'start_time' in session and session['start_time']:
                    start_dt = datetime.combine(selected_date, datetime.strptime(session["start_time"], "%H:%M:%S").time())
                    if 'end_time' in session and session['end_time']:
                        end_dt = datetime.combine(selected_date, datetime.strptime(session["end_time"], "%H:%M:%S").time())
                    else:
                        end_dt = start_dt + timedelta(minutes=session["duration"])
                    session_data.append({
                        "Task": f"⏱️ {session['subject']}",
                        "Start": start_dt,
                        "Finish": end_dt,
                        "Type": "実績"
                    })
        
        # Plotlyでガントチャートを表示
        import plotly.express as px
        import plotly.graph_objects as go
        
        all_data = schedule_data + session_data
        
        if all_data:
            fig = go.Figure()
            
            # 科目名を抽出（絵文字を除く）
            all_subjects = list(set(item["Task"].split(" ")[1] if " " in item["Task"] else item["Task"] for item in all_data))
            subject_to_y = {subject: i for i, subject in enumerate(sorted(all_subjects))}
            
            # 予定を追加（青色）
            for item in schedule_data:
                subject = item["Task"].split(" ")[1] if " " in item["Task"] else item["Task"]
                fig.add_trace(go.Scatter(
                    x=[item["Start"], item["Finish"]],
                    y=[subject_to_y[subject], subject_to_y[subject]],
                    mode='lines+markers',
                    line=dict(color='blue', width=20),
                    name='予定',
                    legendgroup='予定',
                    showlegend=len(schedule_data) > 0,
                    hovertext=f"{item['Task']}<br>{item['Start'].strftime('%H:%M')} - {item['Finish'].strftime('%H:%M')}",
                    hoverinfo='text'
                ))
            
            # 実績を追加（緑色）
            for item in session_data:
                subject = item["Task"].split(" ")[1] if " " in item["Task"] else item["Task"]
                fig.add_trace(go.Scatter(
                    x=[item["Start"], item["Finish"]],
                    y=[subject_to_y[subject], subject_to_y[subject]],
                    mode='lines+markers',
                    line=dict(color='green', width=20),
                    opacity=0.7,
                    name='実績',
                    legendgroup='実績',
                    showlegend=len(session_data) > 0,
                    hovertext=f"{item['Task']}<br>{item['Start'].strftime('%H:%M')} - {item['Finish'].strftime('%H:%M')}",
                    hoverinfo='text'
                ))
            
            fig.update_layout(
                title=f"{selected_date}の予定 vs 実績",
                xaxis_title="時間",
                yaxis_title="科目",
                yaxis=dict(
                    tickmode='array',
                    tickvals=list(subject_to_y.values()),
                    ticktext=list(subject_to_y.keys())
                ),
                height=400,
                hovermode='closest'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"{selected_date}のデータがありません")
        
        st.markdown("---")
        
        # 詳細リスト表示
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📅 予定タイムライン")
            if schedules:
                day_schedules = [
                    s for s in schedules
                    if datetime.strptime(s["date"], "%Y-%m-%d").date() == selected_date
                ]
                
                if day_schedules:
                    for schedule in day_schedules:
                        start_time = datetime.strptime(schedule["start_time"], "%H:%M:%S").strftime("%H:%M")
                        end_time = (datetime.strptime(schedule["start_time"], "%H:%M:%S") + 
                                   timedelta(minutes=schedule["duration"])).strftime("%H:%M")
                        
                        color = "🟢" if schedule["completed"] else "⚪"
                        st.markdown(f"{color} **{start_time} - {end_time}**: {schedule['subject']} ({schedule['duration']}分)")
                        if schedule["notes"]:
                            st.caption(f"   メモ: {schedule['notes']}")
                else:
                    st.info(f"{selected_date}のスケジュールはありません")
            else:
                st.info("スケジュールがまだありません")
        
        with col2:
            st.subheader("⏱️ 実績タイムライン")
            if sessions:
                day_sessions = [
                    s for s in sessions
                    if datetime.strptime(s["date"], "%Y-%m-%d").date() == selected_date
                ]
                
                if day_sessions:
                    for session in day_sessions:
                        icon = "⏱️" if "タイマーからの記録" in session.get("notes", "") else "📝"
                        time_info = ""
                        if 'start_time' in session:
                            time_info = f" ({session['start_time']} - {session.get('end_time', '')})"
                        st.markdown(f"{icon} **{session['subject']}**: {session['duration']}分{time_info}")
                        if session["notes"]:
                            st.caption(f"   メモ: {session['notes']}")
                else:
                    st.info(f"{selected_date}の学習記録はありません")
            else:
                st.info("学習記録がまだありません")
        
        st.markdown("---")
        
        st.subheader("📊 比較サマリー")
        
        scheduled_minutes = sum(
            s["duration"] for s in schedules
            if datetime.strptime(s["date"], "%Y-%m-%d").date() == selected_date
        )
        
        actual_minutes = sum(
            s["duration"] for s in sessions
            if datetime.strptime(s["date"], "%Y-%m-%d").date() == selected_date
        )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("予定学習時間", f"{scheduled_minutes}分")
        
        with col2:
            st.metric("実績学習時間", f"{actual_minutes}分")
        
        with col3:
            diff = actual_minutes - scheduled_minutes
            st.metric("差分", f"{diff:+d}分")
            
            if diff > 0:
                st.success(f"予定より{diff}分多く勉強しました！🎉")
            elif diff < 0:
                st.warning(f"予定より{abs(diff)}分少ないです")
            else:
                st.info("予定通り勉強しました！✅")

# ==================== メイン処理 ====================

# セッション状態の初期化
if 'page' not in st.session_state:
    st.session_state.page = "login"

# ユーザーがログインしているか確認
if 'user' not in st.session_state:
    st.session_state.user = None

# セッション有効性の確認
try:
    user = supabase.auth.get_user()
    if user and 'access_token' in st.session_state:
        set_auth_token(st.session_state.access_token)
except:
    st.session_state.user = None
    st.session_state.access_token = None
    st.session_state.page = "login"

# ページのルーティング
if st.session_state.user is None:
    if st.session_state.page == "signup":
        signup_page()
    else:
        login_page()
else:
    main_app()
