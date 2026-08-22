import urllib.parse, urllib.request, json, sys
KEY = "$$-AquOMqssvNeumkzbGt5HEyt9wzo5BpMVjvNOCKFA5qJI__eUREbVUV4NTuQA_wn"
def fetch(pnu, fmt="json", crs="EPSG:4326"):
    inner = ("http://api.vworld.kr/req/data?service=data&version=2.0&request=GetFeature"
             f"&format={fmt}&size=10&data=LP_PA_CBND_BUBUN&attrFilter=pnu:=:{pnu}"
             f"&crs={crs}&key={KEY}&domain=api.vworld.kr")
    url = "https://www.vworld.kr/proxy.do?url=" + urllib.parse.quote(inner, safe="")
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.vworld.kr/dev/v4dv_2ddataguide2_s003.do?svcIde=cadastral"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
if __name__ == "__main__":
    pnu = sys.argv[1]; crs = sys.argv[2] if len(sys.argv) > 2 else "EPSG:4326"
    print(fetch(pnu, "json", crs))
