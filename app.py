import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import json
import os
import time

# データ保存用ファイル
DATA_FILE = "study_data.json"

# データをロードする関数
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 既存のデータにtimer_sessionsキーがない場合に追加
            if "timer_sessions" not in data:
                data["timer_sessions"] = []
            return data
    return {
        "schedules": [],
        "sessions": [],
        "timer_sessions": [],  # タイマーからの記録用
        "goals": {"daily": 120, "weekly": 600}  # デフォルト: 日次2時間、週次10時間
    }

# データを保存する関数
def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ページ設定
st.set_page_config(
    page_title="学習サポートアプリ",
    page_icon="📚",
    layout="wide"
)

# データをロード
if 'data' not in st.session_state:
    st.session_state.data = load_data()

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

# タイトル
st.title("📚 学習サポートアプリ")
st.markdown("---")

# サイドバーでページ選択
page = st.sidebar.radio(
    "メニュー",
    ["📅 スケジュール管理", "⏱️ タイマー", "🎯 目標設定", "📊 ダッシュボード", "📈 タイムライン比較"]
)

# ==================== スケジュール管理 ====================
if page == "📅 スケジュール管理":
    st.header("📅 学習スケジュール管理")
    
    # 新しいスケジュールを追加
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
                "id": len(st.session_state.data["schedules"]) + 1,
                "subject": subject,
                "date": str(study_date),
                "start_time": str(start_time),
                "duration": duration,
                "notes": notes,
                "completed": False
            }
            st.session_state.data["schedules"].append(new_schedule)
            save_data(st.session_state.data)
            st.success("スケジュールを追加しました！")
            st.rerun()
    
    # スケジュール一覧を表示
    st.subheader("スケジュール一覧")
    if st.session_state.data["schedules"]:
        schedules_df = pd.DataFrame(st.session_state.data["schedules"])
        
        # 日付でソート
        schedules_df['date'] = pd.to_datetime(schedules_df['date'])
        schedules_df = schedules_df.sort_values('date')
        
        for idx, row in schedules_df.iterrows():
            with st.expander(f"{row['date'].strftime('%Y/%m/%d')} - {row['subject']} ({row['duration']}分)"):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**開始時刻:** {row['start_time']}")
                    st.write(f"**メモ:** {row['notes'] if row['notes'] else 'なし'}")
                with col2:
                    if st.button("完了", key=f"complete_{row['id']}"):
                        st.session_state.data["schedules"][idx]["completed"] = True
                        save_data(st.session_state.data)
                        st.rerun()
                    if st.button("削除", key=f"delete_{row['id']}"):
                        st.session_state.data["schedules"].pop(idx)
                        save_data(st.session_state.data)
                        st.rerun()
    else:
        st.info("スケジュールがまだありません。上のフォームから追加してください。")

# ==================== タイマー ====================
elif page == "⏱️ タイマー":
    st.header("⏱️ 学習タイマー")
    
    # 5分前通知のチェック
    now = datetime.now()
    upcoming_schedules = []
    for schedule in st.session_state.data["schedules"]:
        if not schedule["completed"]:
            schedule_date = datetime.strptime(schedule["date"], "%Y-%m-%d").date()
            schedule_time = datetime.strptime(schedule["start_time"], "%H:%M:%S").time()
            schedule_datetime = datetime.combine(schedule_date, schedule_time)
            
            # 今日のスケジュールで、5分前なら通知
            if schedule_date == date.today():
                time_diff = (schedule_datetime - now).total_seconds()
                if 0 < time_diff <= 300:  # 5分以内（300秒）
                    upcoming_schedules.append(schedule)
    
    if upcoming_schedules:
        for schedule in upcoming_schedules:
            st.warning(f"🔔 通知: {schedule['subject']}の勉強時間がもうすぐです！（{schedule['start_time']}開始）")
    
    # タイマーセクション
    st.subheader("勉強タイマー")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        subject = st.text_input("科目名", value=st.session_state.timer_subject, placeholder="例: 数学")
    
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
                    # タイマーを停止して記録入力モードへ
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
    
    # 経過時間の表示
    if st.session_state.timer_running:
        if st.session_state.timer_paused:
            elapsed = st.session_state.timer_elapsed
            st.info(f"⏸️ 一時停止中 - 経過時間: {int(elapsed // 60):02d}:{int(elapsed % 60):02d}")
        else:
            elapsed = st.session_state.timer_elapsed + (time.time() - st.session_state.timer_start_time)
            
            # 大きな時計表示
            st.markdown("---")
            st.subheader("⏱️ 勉強中")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                # 経過時間を大きく表示
                hours = int(elapsed // 3600)
                minutes = int((elapsed % 3600) // 60)
                seconds = int(elapsed % 60)
                
                if hours > 0:
                    time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    time_str = f"{minutes:02d}:{seconds:02d}"
                
                st.markdown(f"<h1 style='text-align: center; font-size: 80px; color: #4CAF50;'>{time_str}</h1>", unsafe_allow_html=True)
                
                # 現在時刻を表示
                current_time = datetime.now().strftime("%H:%M:%S")
                st.markdown(f"<h3 style='text-align: center; color: #666;'>現在時刻: {current_time}</h3>", unsafe_allow_html=True)
                
                st.markdown(f"<p style='text-align: center; font-size: 20px;'>科目: {st.session_state.timer_subject}</p>", unsafe_allow_html=True)
            
            # 自動更新
            time.sleep(1)
            st.rerun()
    
    # タイマー停止後の記録入力ポップアップ
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
                    # 記録を保存
                    new_session = {
                        "id": len(st.session_state.data["sessions"]) + 1,
                        "subject": st.session_state.timer_subject,
                        "date": str(date.today()),
                        "start_time": datetime.fromtimestamp(time.time() - st.session_state.timer_stopped_duration).strftime("%H:%M:%S"),
                        "end_time": datetime.now().strftime("%H:%M:%S"),
                        "duration": int(st.session_state.timer_stopped_duration / 60),
                        "progress": progress,
                        "notes": notes if notes else "タイマーからの記録"
                    }
                    st.session_state.data["sessions"].append(new_session)
                    save_data(st.session_state.data)
                    
                    # 状態をリセット
                    st.session_state.timer_stopped_for_input = False
                    st.session_state.timer_stopped_duration = 0
                    st.success(f"{st.session_state.timer_subject}の学習を記録しました！")
                    st.rerun()
            with col2:
                if st.form_submit_button("キャンセル"):
                    # 状態をリセット（記録しない）
                    st.session_state.timer_stopped_for_input = False
                    st.session_state.timer_stopped_duration = 0
                    st.info("記録をキャンセルしました")
                    st.rerun()
    
    st.markdown("---")
    
    # 手動で学習記録を追加
    st.subheader("手動で学習記録を追加")
    with st.form("manual_session_form"):
        col1, col2 = st.columns(2)
        with col1:
            manual_subject = st.text_input("科目名", placeholder="例: 英語")
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
            # 終了時刻を計算
            start_datetime = datetime.combine(manual_date, manual_start_time)
            end_datetime = start_datetime + timedelta(minutes=manual_duration)
            
            new_session = {
                "id": len(st.session_state.data["sessions"]) + 1,
                "subject": manual_subject,
                "date": str(manual_date),
                "start_time": str(manual_start_time),
                "end_time": end_datetime.strftime("%H:%M:%S"),
                "duration": manual_duration,
                "progress": manual_progress,
                "notes": manual_notes
            }
            st.session_state.data["sessions"].append(new_session)
            save_data(st.session_state.data)
            st.success("学習を記録しました！")
            st.rerun()
    
    st.markdown("---")
    
    # 学習記録一覧（タイマーと手動の記録を統合）
    st.subheader("学習記録一覧")
    if st.session_state.data["sessions"]:
        sessions_df = pd.DataFrame(st.session_state.data["sessions"])
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
                        st.session_state.data["sessions"].pop(idx)
                        save_data(st.session_state.data)
                        st.success("記録を削除しました")
                        st.rerun()
        
        # 合計学習時間
        total_minutes = sessions_df['duration'].sum()
        total_hours = total_minutes / 60
        st.metric("総学習時間", f"{total_hours:.1f}時間 ({total_minutes}分)")
    else:
        st.info("学習記録がまだありません。")

# ==================== 目標設定 ====================
elif page == "🎯 目標設定":
    st.header("🎯 学習目標設定")
    
    st.subheader("目標時間を設定")
    
    col1, col2 = st.columns(2)
    with col1:
        daily_goal = st.number_input(
            "1日の目標学習時間（分）",
            min_value=15,
            max_value=480,
            value=st.session_state.data["goals"]["daily"],
            step=15
        )
    with col2:
        weekly_goal = st.number_input(
            "1週間の目標学習時間（分）",
            min_value=60,
            max_value=1680,
            value=st.session_state.data["goals"]["weekly"],
            step=30
        )
    
    if st.button("目標を保存"):
        st.session_state.data["goals"]["daily"] = daily_goal
        st.session_state.data["goals"]["weekly"] = weekly_goal
        save_data(st.session_state.data)
        st.success("目標を保存しました！")
    
    st.markdown("---")
    
    # 現在の進捗を表示
    st.subheader("現在の進捗")
    
    if st.session_state.data["sessions"]:
        sessions_df = pd.DataFrame(st.session_state.data["sessions"])
        sessions_df['date'] = pd.to_datetime(sessions_df['date'])
        
        # 今日の学習時間
        today = date.today()
        today_sessions = sessions_df[sessions_df['date'].dt.date == today]
        today_minutes = today_sessions['duration'].sum()
        
        # 今週の学習時間
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
            # プログレスバー
            daily_progress = min(today_minutes / daily_goal * 100, 100) if daily_goal > 0 else 0
            st.progress(daily_progress / 100)
            st.caption(f"達成率: {daily_progress:.1f}%")
        
        with col2:
            st.metric(
                "今週の学習時間",
                f"{week_minutes}分 / {weekly_goal}分",
                f"{week_minutes - weekly_goal:+d}分"
            )
            # プログレスバー
            weekly_progress = min(week_minutes / weekly_goal * 100, 100) if weekly_goal > 0 else 0
            st.progress(weekly_progress / 100)
            st.caption(f"達成率: {weekly_progress:.1f}%")
    else:
        st.info("学習記録がまだありません。まずは学習を記録してください。")

# ==================== タイムライン比較 ====================
elif page == "📈 タイムライン比較":
    st.header("📈 予定 vs 実績 タイムライン比較")
    
    # 日付選択
    selected_date = st.date_input("比較する日付", datetime.now())
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 予定タイムライン")
        if st.session_state.data["schedules"]:
            # 選択した日付のスケジュールを抽出
            day_schedules = [
                s for s in st.session_state.data["schedules"]
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
        if st.session_state.data["sessions"]:
            # 選択した日付の記録を抽出
            day_sessions = [
                s for s in st.session_state.data["sessions"]
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
    
    # 比較サマリー
    st.subheader("📊 比較サマリー")
    
    # 予定の合計時間
    scheduled_minutes = sum(
        s["duration"] for s in st.session_state.data["schedules"]
        if datetime.strptime(s["date"], "%Y-%m-%d").date() == selected_date
    )
    
    # 実績の合計時間
    actual_minutes = sum(
        s["duration"] for s in st.session_state.data["sessions"]
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

# ==================== ダッシュボード ====================
elif page == "📊 ダッシュボード":
    st.header("📊 学習ダッシュボード")
    
    if st.session_state.data["sessions"]:
        sessions_df = pd.DataFrame(st.session_state.data["sessions"])
        sessions_df['date'] = pd.to_datetime(sessions_df['date'])
        
        # 科目別の学習時間
        st.subheader("科目別学習時間")
        subject_stats = sessions_df.groupby('subject')['duration'].sum().sort_values(ascending=False)
        
        col1, col2 = st.columns(2)
        with col1:
            st.bar_chart(subject_stats)
        with col2:
            st.dataframe(subject_stats.reset_index().rename(columns={'duration': '総学習時間（分）'}))
        
        # 日別の学習時間
        st.subheader("日別学習時間")
        daily_stats = sessions_df.groupby(sessions_df['date'].dt.date)['duration'].sum()
        st.line_chart(daily_stats)
        
        # 最近の学習記録
        st.subheader("最近の学習記録")
        recent_sessions = sessions_df.sort_values('date', ascending=False).head(5)
        recent_sessions['date'] = recent_sessions['date'].dt.strftime('%Y/%m/%d')
        st.dataframe(recent_sessions[['date', 'subject', 'duration', 'progress', 'notes']], use_container_width=True)
    else:
        st.info("学習記録がまだありません。まずは学習を記録してください。")

# ==================== 通知機能 ====================
st.sidebar.markdown("---")
st.sidebar.subheader("🔔 通知設定")

st.sidebar.info("💡 スケジュールの5分前に自動通知が表示されます")
st.sidebar.caption("※ タイマーページで通知を確認してください")

# フッター
st.sidebar.markdown("---")
st.sidebar.caption("© 2026 学習サポートアプリ")
