"""Estimate player snap shares for seasons without public snap counts (2010-2012).

Fits the relation between a player's listed depth-chart role plus his box-score
production and his real snap share on 2013 and 2014 (the only seasons in the
window with public snap counts), tests it out of sample, then applies it to
2010, 2011 and 2012. Reads downloaded nflverse files only."""
import sys, json, hashlib, numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
D=(sys.argv[1].rstrip('/')+'/') if len(sys.argv)>1 else '/root/nfl/'; OUT=(sys.argv[2].rstrip('/')+'/') if len(sys.argv)>2 else D+'out/'
HIST={'LA':'STL','LAC':'SD','LV':'OAK'}
RWT={'ARZ':'ARI','BLT':'BAL','CLV':'CLE','HST':'HOU','SL':'STL'}
OFFG={'QB':'QB','RB':'RB','HB':'RB','FB':'FB','WR':'WR','TE':'TE','TE/HB':'TE','H-B':'TE','LT':'OL','LG':'OL','C':'OL','RG':'OL','RT':'OL','T':'OL','G':'OL','OL':'OL','LOT':'OL','ROT':'OL','OT':'OL','OG':'OL'}
def defg(s):
    s=s.upper().replace(' ','')
    if s in('LCB','RCB','CB','NB','NCB','DB','NICKEL'): return 'CB'
    if s in('FS','SS','S','SAF'): return 'S'
    if s in('LDE','RDE','DE','LE','RE','DT','NT','LDT','RDT','UT','END','DL','NG','LEO'): return 'DL'
    if 'LB' in s or s in('MIKE','WILL','SAM','WIL','RUSH','JACK','BUCK','MLB','ROVER'): return 'LB'
    return 'OTH'
STK={'K':'K','PK':'K','FG':'K','KO':'K','P':'P','LS':'LS','H':'H','KR':'RET','PR':'RET','KOR':'RET'}
games=pd.read_csv(D+'games.csv',low_memory=False); games=games[games.game_type=='REG']
pl=pd.read_csv(D+'players.csv',low_memory=False).dropna(subset=['pfr_id','gsis_id']).drop_duplicates('pfr_id').set_index('pfr_id').gsis_id
def load(y):
    g=games[games.season==y]
    tg=pd.concat([g.assign(team=g.home_team,opponent=g.away_team),g.assign(team=g.away_team,opponent=g.home_team)])[['game_id','week','gameday','team','opponent']]
    tg['team']=tg.team.replace(HIST); tg['opponent']=tg.opponent.replace(HIST)
    dc=pd.read_csv(D+f'dc_{y}.csv',dtype=str); dc=dc[dc.game_type=='REG'].copy(); dc['week']=dc.week.astype(int); dc['depth']=dc.depth_team.astype(int); dc['slot']=dc.depth_position.fillna('').str.strip()
    dc=dc.drop_duplicates(['club_code','week','gsis_id','formation','slot','depth'])
    dc['n1']=dc.groupby(['club_code','week','formation','slot']).depth.transform(lambda s:(s==1).sum())
    off=dc[dc.formation=='Offense'].copy(); off['grp']=off.slot.map(OFFG).fillna('OTH')
    de=dc[dc.formation=='Defense'].copy(); de['grp']=de.slot.map(defg)
    stt=dc[dc.formation=='Special Teams'].copy(); stt['grp']=stt.slot.map(STK).fillna('OTH')
    key=['club_code','week','gsis_id']
    o=off.sort_values('depth').drop_duplicates(key)[key+['grp','depth','n1','slot']].rename(columns={'grp':'off_grp','depth':'off_depth','n1':'off_n1','slot':'off_slot'})
    d=de.sort_values('depth').drop_duplicates(key)[key+['grp','depth','n1','slot']].rename(columns={'grp':'def_grp','depth':'def_depth','n1':'def_n1','slot':'def_slot'})
    s=stt.sort_values('depth').groupby(key).agg(st_grp=('grp','first'),st_depth=('depth','min'),st_slots=('slot','nunique')).reset_index()
    base=dc.sort_values('depth').drop_duplicates(key)[key+['full_name','position']]
    ch=base.merge(o,on=key,how='left').merge(d,on=key,how='left').merge(s,on=key,how='left').rename(columns={'club_code':'team','gsis_id':'player_id','position':'chart_position'})
    st=pd.read_csv(D+f'st_{y}.csv',low_memory=False); st=st[st.season_type=='REG'].copy(); st['team']=st.team.replace(HIST)
    num=['attempts','sacks_suffered','carries','targets','receptions','def_tackles_solo','def_tackle_assists','def_tackles_with_assist','def_sacks','def_qb_hits','def_interceptions','def_pass_defended','def_tackles_for_loss','punt_returns','kickoff_returns','fg_att','pat_att','pt_att','penalties','fumble_recovery_own','fumble_recovery_opp']
    for c in num: st[c]=pd.to_numeric(st[c],errors='coerce').fillna(0)
    st['tk']=st.def_tackles_solo+st.def_tackle_assists
    st=st[['player_id','player_display_name','position','position_group','week','team']+num+['tk']].drop_duplicates(['player_id','week','team'])
    tt=st.groupby(['team','week']).agg(t_att=('attempts','sum'),t_sk=('sacks_suffered','sum'),t_car=('carries','sum'),t_tgt=('targets','sum'),t_tk=('tk','sum')).reset_index(); tt['t_plays']=tt.t_att+tt.t_sk+tt.t_car
    rw=pd.read_csv(D+f'rw_{y}.csv',low_memory=False); rw=rw[rw.game_type=='REG'].copy(); rw['team']=rw.team.replace(RWT); rw['week']=rw.week.astype(int)
    rw=rw.dropna(subset=['gsis_id']).rename(columns={'gsis_id':'player_id','full_name':'roster_name','position':'roster_position'})
    rw['inactive']=rw.status_description_abbr.astype(str).str.startswith('I').astype(int)
    rw=rw.sort_values('inactive').drop_duplicates(['player_id','week','team'])[['player_id','week','team','roster_name','roster_position','inactive']]; rw['on_roster']=1
    f=ch.merge(st,on=['player_id','week','team'],how='outer').merge(rw,on=['player_id','week','team'],how='outer')
    f=f.merge(tg,on=['team','week'],how='inner')            # drops bye weeks and non-game rows
    f=f.merge(tt,on=['team','week'],how='left').merge(tt[['team','week','t_plays']].rename(columns={'team':'opponent','t_plays':'o_plays'}),on=['opponent','week'],how='left')
    f['season']=y
    f['has_stat_tmp']=f.player_display_name.notna().astype(int)
    f['player_name']=f.player_display_name.fillna(f.full_name).fillna(f.roster_name); f['pos']=f.position.fillna(f.chart_position).fillna(f.roster_position)
    f['inactive']=f.inactive.fillna(0); f['on_roster']=f.on_roster.fillna(0)
    f.loc[f.has_stat_tmp==1,'inactive']=0
    for c in num+['tk']: f[c]=f[c].fillna(0)
    f['has_stat']=f.player_display_name.notna().astype(int); f['on_chart']=f.full_name.notna().astype(int)
    f['tgt_sh']=f.targets/f.t_tgt.clip(lower=1); f['car_sh']=f.carries/f.t_car.clip(lower=1); f['att_sh']=f.attempts/f.t_att.clip(lower=1); f['tk_sh']=f.tk/f.t_tk.clip(lower=1)
    for c in ['off_depth','def_depth','st_depth']: f[c]=f[c].fillna(9)
    for c in ['off_n1','def_n1','st_slots']: f[c]=f[c].fillna(0)
    # season-level role context (same season)
    gp=f.groupby('player_id')
    f['s_off1']=gp.off_depth.transform(lambda s:(s==1).mean()); f['s_def1']=gp.def_depth.transform(lambda s:(s==1).mean())
    f['s_tgt']=gp.tgt_sh.transform('mean'); f['s_car']=gp.car_sh.transform('mean'); f['s_tk']=gp.tk_sh.transform('mean'); f['s_stat']=gp.has_stat.transform('mean')
    f=f.sort_values(['player_id','week'])
    for c in ['off_depth','def_depth']:
        f[c+'_prev']=f.groupby('player_id')[c].shift(1).fillna(f[c]); f[c+'_next']=f.groupby('player_id')[c].shift(-1).fillna(f[c])
    return f,tg
def targets(y,f):
    sc=pd.read_csv(D+f'sc_{y}.csv'); sc=sc[sc.game_type=='REG'].copy(); sc['player_id']=sc.pfr_player_id.map(pl)
    unm=sc.player_id.isna().sum(); sc=sc.dropna(subset=['player_id'])
    sc=sc.groupby(['player_id','game_id']).agg(offense_snaps=('offense_snaps','sum'),offense_pct=('offense_pct','max'),defense_snaps=('defense_snaps','sum'),defense_pct=('defense_pct','max'),st_snaps=('st_snaps','sum'),st_pct=('st_pct','max')).reset_index()
    m=f.merge(sc,on=['player_id','game_id'],how='left')
    notin=len(sc)-m.offense_snaps.notna().sum()
    for c in ['offense_snaps','offense_pct','defense_snaps','defense_pct','st_snaps','st_pct']: m[c]=m[c].fillna(0)
    ts=pd.read_csv(D+f'sc_{y}.csv'); ts=ts[ts.game_type=='REG'].groupby(['game_id','team']).agg(team_off=('offense_snaps','max'),team_def=('defense_snaps','max')).reset_index()
    m=m.merge(ts,on=['game_id','team'],how='left')
    return m,int(unm),int(notin)
CAT=['off_grp','def_grp','st_grp','position_group']
FO=['inactive','on_roster','off_depth','off_n1','off_depth_prev','off_depth_next','def_depth','st_depth','st_slots','tgt_sh','car_sh','att_sh','targets','carries','attempts','receptions','has_stat','on_chart','penalties','s_off1','s_tgt','s_car','s_stat','t_plays']
FD=['inactive','on_roster','def_depth','def_n1','def_depth_prev','def_depth_next','off_depth','st_depth','tk','tk_sh','def_sacks','def_qb_hits','def_pass_defended','def_interceptions','def_tackles_for_loss','has_stat','on_chart','penalties','s_def1','s_tk','s_stat','o_plays']
FS=['inactive','on_roster','st_depth','st_slots','off_depth','def_depth','punt_returns','kickoff_returns','fg_att','pat_att','pt_att','tk','has_stat','on_chart','s_off1','s_def1','s_stat']
def X(f,cols):
    x=f[cols].copy()
    for c in CAT: x[c]=f[c].fillna('NONE').astype('category')
    return x
def fit(tr,cols,y):
    cats=sorted(set().union(*[set(tr[c].fillna('NONE')) for c in CAT]))
    m=HistGradientBoostingRegressor(max_iter=300,learning_rate=0.06,max_leaf_nodes=31,min_samples_leaf=40,categorical_features=list(range(len(cols),len(cols)+len(CAT))),random_state=0)
    xt=X(tr,cols); 
    for c in CAT: xt[c]=xt[c].cat.set_categories(ALLC[c])
    m.fit(xt,tr[y]); return m
def pred(m,f,cols):
    x=X(f,cols)
    for c in CAT: x[c]=x[c].cat.set_categories(ALLC[c])
    return np.where(f.inactive.values==1,0.0,np.clip(m.predict(x),0,1))
frames={}; sched={}
for y in range(2010,2015): frames[y],sched[y]=load(y)
ALLC={c:sorted(set().union(*[set(frames[y][c].fillna('NONE')) for y in frames])) for c in CAT}
tr={}; info={}
for y in (2013,2014): tr[y],u,n=targets(y,frames[y]); info[y]={'snap_rows_without_player_id':u,'snap_rows_not_joined_to_a_chart_or_stat_row':n,'rows':len(tr[y])}
# team snap proxy
allt=pd.concat(tr.values()); tgm=allt.drop_duplicates(['game_id','team'])
a_off=np.polyfit(tgm.t_plays,tgm.team_off,1); a_def=np.polyfit(tgm.o_plays,tgm.team_def,1)
team_fit={'offense':{'slope':float(a_off[0]),'intercept':float(a_off[1]),'mae':float(np.abs(np.polyval(a_off,tgm.t_plays)-tgm.team_off).mean())},'defense':{'slope':float(a_def[0]),'intercept':float(a_def[1]),'mae':float(np.abs(np.polyval(a_def,tgm.o_plays)-tgm.team_def).mean())}}
def grp(f): return np.where(f.off_grp.notna()&(f.off_depth<=f.def_depth),f.off_grp,np.where(f.def_grp.notna(),f.def_grp,f.position_group.fillna(f.st_grp).fillna('NONE')))
val={}
for a,b in ((2013,2014),(2014,2013)):
    mo=fit(tr[a],FO,'offense_pct'); md=fit(tr[a],FD,'defense_pct'); ms=fit(tr[a],FS,'st_pct')
    t=tr[b].copy(); t['po']=pred(mo,t,FO); t['pd']=pred(md,t,FD); t['ps']=pred(ms,t,FS); t['g']=grp(t)
    t['eo']=t.po*np.polyval(a_off,t.t_plays); t['ed']=t.pd*np.polyval(a_def,t.o_plays)
    r={'fit_on':a,'tested_on':b,'player_games':len(t)}
    r['game_mae_pct_points']={'offense':round(float(np.abs(t.po-t.offense_pct).mean()*100),2),'defense':round(float(np.abs(t.pd-t.defense_pct).mean()*100),2),'special_teams':round(float(np.abs(t.ps-t.st_pct).mean()*100),2)}
    # naive baseline: mean share by group and depth from the fit season
    bo=tr[a].assign(g=grp(tr[a])).groupby(['g','off_depth']).offense_pct.mean(); bd=tr[a].assign(g=grp(tr[a])).groupby(['g','def_depth']).defense_pct.mean()
    t['bo']=[bo.get((g,d),0) for g,d in zip(t.g,t.off_depth)]; t['bd']=[bd.get((g,d),0) for g,d in zip(t.g,t.def_depth)]
    r['baseline_game_mae_pct_points']={'offense':round(float(np.abs(t.bo-t.offense_pct).mean()*100),2),'defense':round(float(np.abs(t.bd-t.defense_pct).mean()*100),2)}
    s=t.groupby(['player_id','g']).agg(ao=('offense_snaps','sum'),eo=('eo','sum'),ad=('defense_snaps','sum'),ed=('ed','sum')).reset_index()
    s['a']=s.ao+s.ad; s['e']=s.eo+s.ed
    r['season']={'players':len(s),'corr_actual_vs_estimate':round(float(np.corrcoef(s.a,s.e)[0,1]),4),'mae_snaps':round(float(np.abs(s.a-s.e).mean()),1)}
    big=s[s.a>=200]; r['season']['players_200_plus_snaps']=len(big); r['season']['median_abs_pct_error_200_plus']=round(float((np.abs(big.a-big.e)/big.a).median()*100),1); r['season']['share_within_15_pct_200_plus']=round(float(((np.abs(big.a-big.e)/big.a)<=0.15).mean()*100),1)
    bg={}
    for g,x in big.groupby('g'):
        if len(x)>=15: bg[g]={'players':len(x),'median_abs_pct_error':round(float((np.abs(x.a-x.e)/x.a).median()*100),1),'share_within_15_pct':round(float(((np.abs(x.a-x.e)/x.a)<=0.15).mean()*100),1)}
    r['season_by_group_200_plus']=bg; val[f'{a}_to_{b}']=r
# final fit on both seasons, estimate 2010-2012
both=pd.concat([tr[2013],tr[2014]]); mo=fit(both,FO,'offense_pct'); md=fit(both,FD,'defense_pct'); ms=fit(both,FS,'st_pct')
files={}
for y in (2010,2011,2012):
    f=frames[y].copy(); f['po']=pred(mo,f,FO); f['pd']=pred(md,f,FD); f['ps']=pred(ms,f,FS)
    f['team_offense_snaps_est']=np.polyval(a_off,f.t_plays).round(1); f['team_defense_snaps_est']=np.polyval(a_def,f.o_plays).round(1)
    o=pd.DataFrame({'season':y,'week':f.week,'game_date':f.gameday,'team':f.team,'opponent':f.opponent,'player_name':f.player_name,'player_id':f.player_id,'position':f.pos,
        'offense_snaps_est':(f.po*f.team_offense_snaps_est).round(1),'offense_pct_est':(f.po*100).round(1),'defense_snaps_est':(f.pd*f.team_defense_snaps_est).round(1),'defense_pct_est':(f.pd*100).round(1),'st_snaps_est':'','st_pct_est':(f.ps*100).round(1),
        'team_offense_snaps_est':f.team_offense_snaps_est,'team_defense_snaps_est':f.team_defense_snaps_est,
        'chart_offense_slot':f.off_slot,'chart_offense_depth':f.off_depth.replace(9,np.nan),'chart_defense_slot':f.def_slot,'chart_defense_depth':f.def_depth.replace(9,np.nan),'on_depth_chart':f.on_chart,'has_box_score_line':f.has_stat,'on_weekly_roster':f.on_roster.astype(int),'gameday_inactive':f.inactive.astype(int)})
    o=o[o.player_id.notna()].sort_values(['week','team','player_name'])
    for c in ['chart_offense_depth','chart_defense_depth']: o[c]=o[c].map(lambda v:'' if pd.isna(v) else int(v))
    p=OUT+f'snap_estimates_{y}.csv'; o.to_csv(p,index=False)
    files[y]={'rows':len(o),'players':int(o.player_id.nunique()),'team_games':int(o.drop_duplicates(['team','week']).shape[0]),'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest()}
json.dump({'training':info,'team_snap_proxy':team_fit,'validation':val,'files':files},open(OUT+'snap_estimates_validation.json','w'),indent=1)
print(json.dumps({'training':info,'team_snap_proxy':team_fit,'validation':val,'files':files},indent=1))
