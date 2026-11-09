import numpy as np
from openai import OpenAI
c = OpenAI(base_url="http://127.0.0.1:3004/v1", api_key="local")
q = "훈민정음은 언제 만들어졌나요?"
docs = ["세종대왕은 1443년에 훈민정음을 창제하고 1446년에 이를 반포하였다.",
        "김치는 배추나 무를 소금에 절인 뒤 고춧가루와 젓갈을 넣어 발효시킨 음식이다.",
        "한라산은 해발 1,947m로 남한에서 가장 높은 산이며 제주도 중앙에 자리한다."]
qe = np.array(c.embeddings.create(model="kure-v3", input=q, extra_body={"input_type": "query"}).data[0].embedding)
de = np.array([e.embedding for e in c.embeddings.create(model="kure-v3", input=docs, extra_body={"input_type": "passage"}).data])
print("dim", qe.shape[0], "scores", (de @ qe).round(4), "expected ~[0.5386 0.0152 -0.0211]")
