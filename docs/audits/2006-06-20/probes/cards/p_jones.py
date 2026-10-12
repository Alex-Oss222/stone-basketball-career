import sys; sys.path.insert(0, '/home/user/stone-basketball-career')
from runtime import club_truth
for d in ["2005-11-01","2006-01-06","2006-01-07","2006-01-08","2006-04-19","2006-06-20"]:
    print(d, club_truth.holder("jonesju01","Jumaine Jones", d))
