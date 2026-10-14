import hashlib
import subprocess
from PIL import Image, ImageDraw
from factory.scaffold import scaffold
from factory.policy import ROOT
from office.store import now


def create_sample(store):
    try: commit = subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    except Exception: commit = "e4ad659632671392bf96bc6db044fb168c17c3d7"
    c = scaffold(["ru","en","hy"],commit)
    cid,timestamp = c["clinicId"],now()
    def fact(v): return {"value":v,"status":"VERIFIED","sourceIds":["synthetic-material"],"checkedAt":timestamp,"reviewer":"synthetic-test"}
    def loc(ru,en,hy): return {"ru":fact(ru),"en":fact(en),"hy":fact(hy)}
    c["synthetic"] = True
    c["sources"] = [{"id":"synthetic-material","clinicId":cid,"kind":"client_material","url":None,"documentRef":"synthetic-owned-test-material",
                      "retrievedAt":timestamp,"accessStatus":"ALLOWED","contentHash":None}]
    c["brand"]["name"] = fact("Тестовая клиника Order & Profit")
    c["brand"]["description"] = loc("Тестовая карточка для проверки системы. Это не действующая клиника.","A synthetic card for system testing, not an actual clinic.","Համակարգի ստուգման փորձնական քարտ, ոչ գործող կլինիկա։")
    c["contact"]["country"] = fact("Армения");c["contact"]["city"] = fact("Ереван")
    c["contact"]["email"] = fact("test@example.invalid")
    card = store.create("Тестовая клиника Order & Profit","Армения","Ереван","ru",commit,True,c)
    path = store.root/"assets"/cid/"synthetic-illustration"
    image = Image.new("RGB",(960,720),"#f1ebe0")
    draw = ImageDraw.Draw(image);draw.rounded_rectangle((130,100,830,620),radius=60,fill="#b8925a")
    draw.rectangle((330,230,630,470),fill="#faf7f1")
    image.save(path,format="PNG")
    data = path.read_bytes()
    c["assets"] = [{"id":"owned-illustration","storageRef":path.name,"sha256":hashlib.sha256(data).hexdigest(),"mime":"image/png","bytes":len(data),
                    "scope":"shared","subjectClinicId":None,"depiction":"generic_illustration",
                    "rights":{"status":"PERMITTED","sourceIds":["synthetic-material"],"proofRef":"synthetic-self-created-geometry","allowedUses":["demo"],"expiresAt":None}}]
    c["media"]["hero"] = fact("owned-illustration")
    return store.save(cid,card["version"],c)
