# fix/empty-message-id (ca94d6e) — hk-council-opus-a
Score: 9

No findings. The ValueError is raised while the arguments are evaluated, before command() runs, so nothing is sent (checked STAT/ARTICLE/HEAD/BODY at nntp.py:1399-1581, plus _hdr:1593, over:1689 and xpat:1796). bool is rejected before the int path. Not verified on a host.
