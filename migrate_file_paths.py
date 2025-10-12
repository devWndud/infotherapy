#!/usr/bin/env python3
"""
기존 데이터베이스의 절대 경로를 상대 경로로 마이그레이션하는 스크립트
"""

import sqlite3
import json
import os
from pathlib import Path

def migrate_file_paths():
    # 데이터베이스 경로
    db_path = "infotherapy.db"
    uploads_dir = "uploads"
    
    if not os.path.exists(db_path):
        print(f"데이터베이스 파일을 찾을 수 없습니다: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # assignments 테이블의 file_paths 컬럼 업데이트
        print("assignments 테이블의 file_paths 마이그레이션 중...")
        assignments = cursor.execute("SELECT id, file_paths FROM assignments WHERE file_paths IS NOT NULL AND file_paths != ''").fetchall()
        
        for assignment in assignments:
            try:
                file_paths = json.loads(assignment['file_paths'])
                updated_paths = []
                
                for file_path in file_paths:
                    if isinstance(file_path, str):
                        # 절대 경로에서 파일명만 추출
                        filename = os.path.basename(file_path)
                        updated_paths.append(filename)
                    else:
                        updated_paths.append(file_path)
                
                # 업데이트
                cursor.execute("UPDATE assignments SET file_paths = ? WHERE id = ?", 
                             (json.dumps(updated_paths), assignment['id']))
                print(f"  Assignment {assignment['id']}: {len(file_paths)} 파일 경로 업데이트")
                
            except json.JSONDecodeError:
                print(f"  Assignment {assignment['id']}: JSON 파싱 오류, 건너뜀")
                continue
        
        # submissions 테이블의 file_paths 컬럼 업데이트
        print("submissions 테이블의 file_paths 마이그레이션 중...")
        submissions = cursor.execute("SELECT id, file_paths FROM submissions WHERE file_paths IS NOT NULL AND file_paths != ''").fetchall()
        
        for submission in submissions:
            try:
                file_paths = json.loads(submission['file_paths'])
                updated_paths = []
                
                for file_path in file_paths:
                    if isinstance(file_path, str):
                        # 절대 경로에서 파일명만 추출
                        filename = os.path.basename(file_path)
                        updated_paths.append(filename)
                    else:
                        updated_paths.append(file_path)
                
                # 업데이트
                cursor.execute("UPDATE submissions SET file_paths = ? WHERE id = ?", 
                             (json.dumps(updated_paths), submission['id']))
                print(f"  Submission {submission['id']}: {len(file_paths)} 파일 경로 업데이트")
                
            except json.JSONDecodeError:
                print(f"  Submission {submission['id']}: JSON 파싱 오류, 건너뜀")
                continue
        
        # 기존 file_path 컬럼도 업데이트 (단일 파일)
        print("기존 file_path 컬럼 마이그레이션 중...")
        
        # assignments 테이블
        assignments_single = cursor.execute("SELECT id, file_path FROM assignments WHERE file_path IS NOT NULL AND file_path != ''").fetchall()
        for assignment in assignments_single:
            filename = os.path.basename(assignment['file_path'])
            cursor.execute("UPDATE assignments SET file_path = ? WHERE id = ?", 
                         (filename, assignment['id']))
            print(f"  Assignment {assignment['id']}: 단일 파일 경로 업데이트")
        
        # submissions 테이블
        submissions_single = cursor.execute("SELECT id, file_path FROM submissions WHERE file_path IS NOT NULL AND file_path != ''").fetchall()
        for submission in submissions_single:
            filename = os.path.basename(submission['file_path'])
            cursor.execute("UPDATE submissions SET file_path = ? WHERE id = ?", 
                         (filename, submission['id']))
            print(f"  Submission {submission['id']}: 단일 파일 경로 업데이트")
        
        # 변경사항 저장
        conn.commit()
        print("마이그레이션 완료!")
        
    except Exception as e:
        print(f"오류 발생: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_file_paths()
