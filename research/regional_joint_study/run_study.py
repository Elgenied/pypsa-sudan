"""Resumable batch driver. No language-model calls; one memory-isolated solver job at a time."""
from pathlib import Path
import argparse
import datetime
import json
import os
import subprocess
import sys
import traceback
import html
import shutil
import time
import model as m


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def run(solver='gurobi', selected=None, wait_pid=None, mirror=None, publish=False):
    m.OUT.mkdir(parents=True,exist_ok=True)
    logdir=m.HERE/'logs';logdir.mkdir(exist_ok=True)
    lock=m.HERE/'batch.lock'
    # OS locks are released after a crash, allowing safe resume without stale-lock deletion.
    guard=lock.open('a+b')
    if lock.stat().st_size==0:guard.write(b'0');guard.flush()
    guard.seek(0)
    if os.name=='nt':
        import msvcrt
        msvcrt.locking(guard.fileno(),msvcrt.LK_NBLCK,1)
    else:
        import fcntl
        fcntl.flock(guard,fcntl.LOCK_EX|fcntl.LOCK_NB)
    status=dict(started_UTC=now(),pid=os.getpid(),solver=solver,state='running',total_cases=len(selected or m.cases()),completed=[],active=None)
    mirror=Path(mirror).resolve() if mirror else None
    if mirror:
        assert mirror!=m.HERE.resolve() and m.HERE.resolve() not in mirror.parents
        mirror.mkdir(parents=True,exist_ok=True)
    def save():
        status['updated_UTC']=now()
        temp=m.HERE/'STATUS.tmp'
        temp.write_text(json.dumps(status,indent=2),encoding='utf-8')
        temp.replace(m.HERE/'STATUS.json')
        active=html.escape(str(status['active'] or 'None'))
        page=f'''<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="30">
        <title>Sudan regional study — run status</title><style>body{{font:18px system-ui;max-width:900px;margin:60px auto;line-height:1.6}}progress{{width:100%}}code{{font-size:15px}}</style>
        <h1>Sudan regional study</h1><p>State: <b>{status['state']}</b></p>
        <p>{len(status['completed'])} of {status['total_cases']} cases completed, replayed and checked.</p>
        <progress value="{len(status['completed'])}" max="{status['total_cases']}"></progress>
        <p>Active step: <code>{active}</code></p><p>Updated UTC: {status['updated_UTC']}</p>
        <p>This page refreshes every 30 seconds. Computation runs in Python without language-model calls.</p>
        <p><a href="Sudan_Regional_Joint_Study.html">Open completed study report</a> · <a href="STATUS.json">Detailed status</a></p>
        <p>{html.escape(status.get('error',status.get('publication_error','')))}</p>
        <p>Published commit: <code>{html.escape(status.get('published_commit','Not yet published'))}</code></p>'''
        (m.HERE/'RUN_STATUS.html').write_text(page,encoding='utf-8')
        if mirror:
            for name in ['STATUS.json','RUN_STATUS.html']:
                shutil.copy2(m.HERE/name,mirror/name)
    try:
        if wait_pid:
            import psutil
            status['active']=dict(phase='waiting_for_initial_case',pid=wait_pid);save()
            try:
                process=psutil.Process(wait_pid)
                assert 'regional_joint_study' in ' '.join(process.cmdline()), 'Unexpected process'
                process.wait()
            except psutil.NoSuchProcess:
                pass
        # Finish replay/checks for saved investments before starting fresh expensive solves.
        queue = selected if selected is not None else sorted(
            m.cases(), key=lambda c: not (m.OUT/c.key/'manifest.json').exists())
        for c in queue:
            for phase in ['solve','replay','check']:
                status['active']=dict(case=c.key,phase=phase);save()
                if phase=='check':
                    cmd=[sys.executable,str(m.HERE/'check.py'),'--case',c.key]
                else:
                    cmd=[sys.executable,str(m.HERE/'model.py'),c.key,'--solver',solver,'--phase',phase]
                with (logdir/f'{c.key}_{phase}.log').open('w',encoding='utf-8') as out:
                    subprocess.run(cmd,cwd=m.ROOT,stdout=out,stderr=subprocess.STDOUT,check=True)
            status['completed'].append(c.key);save()
            if mirror:
                shutil.copytree(m.OUT/c.key,mirror/'results'/c.key,dirs_exist_ok=True)
        if selected is None:
            for script in ['check.py','report.py']:
                status['active']=dict(phase=script);save()
                with (logdir/(script+'.log')).open('w',encoding='utf-8') as out:
                    subprocess.run([sys.executable,str(m.HERE/script)],cwd=m.ROOT,stdout=out,stderr=subprocess.STDOUT,check=True)
        status.update(state='complete',active=None,finished_UTC=now());save()
        if publish and selected is None:
            try:
                scope='research/regional_joint_study'
                branch=subprocess.check_output(['git','branch','--show-current'],cwd=m.ROOT,text=True).strip()
                assert branch=='main', 'Expected main branch; publication deferred'
                staged=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=m.ROOT,text=True).splitlines()
                assert all(p.startswith(scope+'/') for p in staged), 'Unrelated staged changes; publication deferred'
                subprocess.run(['git','add',scope],cwd=m.ROOT,check=True)
                changed=subprocess.run(['git','diff','--cached','--quiet'],cwd=m.ROOT).returncode
                if changed:
                    subprocess.run(['git','commit','-m','Complete full-year six-state recovery study and validated notebook'],cwd=m.ROOT,check=True)
                subprocess.run(['git','push','origin','main'],cwd=m.ROOT,check=True)
                status['published_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=m.ROOT,text=True).strip()
            except Exception as exc:
                status['publication_error']=str(exc)
            save()
        if mirror:
            shutil.copytree(m.HERE,mirror,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','logs','batch.lock','*.tmp','batch_stdout.log','batch_stderr.log'))
    except BaseException as exc:
        status.update(state='failed',error=str(exc),traceback=traceback.format_exc());save()
        raise
    finally:
        guard.close()


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--solver',choices=['gurobi','highs'],default='gurobi');p.add_argument('--case');p.add_argument('--wait-pid',type=int);p.add_argument('--mirror');p.add_argument('--publish',action='store_true');a=p.parse_args()
    run(a.solver,[next(c for c in m.cases() if c.key==a.case)] if a.case else None,a.wait_pid,a.mirror,a.publish)
