from urllib import parse
import yarl

print(yarl.URL("https://music.youtube.com/playlist?list=PL4fGSI1pDJn6puJdseH2Rt9sMvt9E2M4i&feature=share").query)
print(yarl.URL("https://open.spotify.com/track/63irPUP3xB74fHdw1Aw9zR?si=8a40acc291df4ae1").parts)
print(yarl.URL("f hfghfghfghfgh").host)