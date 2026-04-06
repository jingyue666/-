import streamlit as st
import time
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

# ===================== 混元AI客户端（格式严格校验）=====================
class HunyuanClient:
    def __init__(self, secret_id, secret_key):
        self.cred = credential.Credential(secret_id, secret_key)
        self.httpProfile = HttpProfile()
        self.httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
        self.clientProfile = ClientProfile()
        self.clientProfile.httpProfile = self.httpProfile
        self.client = hunyuan_client.HunyuanClient(self.cred, "ap-beijing", self.clientProfile)

    def chat(self, prompt, system_prompt):
        try:
            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            req.Messages = [
                {"Role": "system", "Content": system_prompt},
                {"Role": "user", "Content": prompt}
            ]
            req.Temperature = 0.7
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
        except Exception as e:
            raise e

    def chat_with_history(self, messages, system_prompt):
        try:
            req = models.ChatCompletionsRequest()
            req.Model = "hunyuan-standard"
            # 1. 只保留合法角色，彻底过滤tool/错误消息
            full_messages = [{"Role": "system", "Content": system_prompt}]
            for msg in messages:
                if msg["role"] not in ["user", "assistant"]:
                    continue
                role = "assistant" if msg["role"] == "assistant" else "user"
                full_messages.append({"Role": role, "Content": msg["content"]})
            
            # 2. 强制校验：必须以user结尾，否则直接抛出明确错误
            if not full_messages or full_messages[-1]["Role"] != "user":
                raise ValueError("对话格式错误，必须以用户提问结尾")
            
            req.Messages = full_messages
            req.Temperature = 0.7
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
        except Exception as e:
            raise e

# ===================== 页面配置 =====================
st.set_page_config(page_title="司法流程辅助系统", layout="wide")
st.title("⚖️ 司法流程辅助与节点提醒系统")

# 🔴 核心：严格初始化会话状态，杜绝脏数据
if "hy_client" not in st.session_state:
    st.session_state.hy_client = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "mode" not in st.session_state:
    st.session_state.mode = "通俗解答"

# ===================== 登录 =====================
if st.session_state.hy_client is None:
    st.subheader("🔐 登录系统")
    secret_id = st.text_input("SecretId")
    secret_key = st.text_input("SecretKey", type="password")

    if st.button("登录"):
        if not secret_id or not secret_key:
            st.error("密钥不能为空！")
        else:
            try:
                cli = HunyuanClient(secret_id, secret_key)
                cli.chat("测试", "你只需要回复‘正常’")
                st.session_state.hy_client = cli
                st.success("✅ 登录成功")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 登录失败：{str(e)}")
    st.stop()

# ===================== 功能模式（通俗化）=====================
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("📚 通俗讲法律"):
        st.session_state.mode = "通俗解答"
with c2:
    if st.button("⏰ 流程时间提醒"):
        st.session_state.mode = "节点提醒"
with c3:
    if st.button("💬 日常聊天咨询"):
        st.session_state.mode = "智能对话"
with c4:
    if st.button("📄 简单文书模板"):
        st.session_state.mode = "文书生成"

st.info(f"当前模式：**{st.session_state.mode}**")

# 🔴 核心：清空对话时彻底重置，杜绝残留
if st.button("🗑 清空对话"):
    st.session_state.messages = []
    st.rerun()

# 只渲染合法的user/assistant消息
for msg in st.session_state.messages:
    if msg["role"] in ["user", "assistant"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 输入框
prompt = st.chat_input("随便问，用大白话回答你")

if prompt:
    # 🔴 核心：只添加合法的user消息，不允许任何其他角色混入
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 通俗化系统提示词
    system_prompt = {
        "通俗解答": """
            你要用超级大白话解释法律，不许用专业术语。
            别人怎么通俗问，你就怎么通俗答。
            不要讲法条编号，不要讲难懂词汇，像聊天一样回答。
            说人话，说简单话，说清楚话。
        """,
        "节点提醒": """
            用最简单的话讲流程、时间、步骤。
            分点说清楚，不要复杂，不要专业词。
            让普通人一眼看懂什么时候该做什么。
        """,
        "智能对话": """
            你是贴心顾问，别人怎么说你就怎么回。
            完全口语化，不生硬，不官方，不摆架子。
            不懂的地方你主动用简单话解释清楚。
        """,
        "文书生成": """
            生成简单、实用、普通人能直接用的文书模板。
            结构清晰，内容简单，去掉复杂格式，直接能用。
        """
    }[st.session_state.mode]

    with st.chat_message("assistant"):
        with st.spinner("正在用大白话思考..."):
            try:
                # 🔴 核心：双重过滤+格式校验，100%合规
                # 1. 过滤非法角色
                clean_history = []
                for m in st.session_state.messages[:-1]:
                    if m["role"] in ["user", "assistant"]:
                        clean_history.append(m)
                
                # 2. 强制校验：必须以user结尾
                if not clean_history or clean_history[-1]["role"] != "user":
                    raise ValueError("对话格式错误，必须以用户提问结尾")
                
                # 3. 调用API
                res = st.session_state.hy_client.chat_with_history(
                    clean_history, system_prompt
                )
                st.markdown(res)
                # 4. 只添加合法的assistant回复
                st.session_state.messages.append({"role": "assistant", "content": res})
            except Exception as e:
                # 🔴 核心：错误消息不写入对话历史，避免污染格式
                err = f"请求失败：{str(e)}"
                st.error(err)
