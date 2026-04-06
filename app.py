import streamlit as st
import time
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models

# ===================== 混元AI客户端 =====================
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
            
            full_messages = [{"Role": "system", "Content": system_prompt}]
            
            for msg in messages:
                if msg["role"] not in ["user", "assistant"]:
                    continue
                role = "assistant" if msg["role"] == "assistant" else "user"
                full_messages.append({"Role": role, "Content": msg["content"]})
            
            req.Messages = full_messages
            req.Temperature = 0.7
            resp = self.client.ChatCompletions(req)
            return resp.Choices[0].Message.Content
        except Exception as e:
            raise e

# ===================== 页面配置 =====================
st.set_page_config(page_title="司法流程辅助系统", layout="wide")
st.title("⚖️ 司法流程辅助与节点提醒系统")

# 会话状态初始化
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
                cli.chat("测试", "你只需要回复'正常'")
                st.session_state.hy_client = cli
                st.success("✅ 登录成功")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 登录失败：{str(e)}")
    st.stop()

# ===================== 功能模式 =====================
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("📚 通俗讲法律"):
        st.session_state.mode = "通俗解答"
        st.session_state.messages = []  # 切换模式清空对话
        st.rerun()
with c2:
    if st.button("⏰ 流程时间提醒"):
        st.session_state.mode = "节点提醒"
        st.session_state.messages = []
        st.rerun()
with c3:
    if st.button("💬 日常聊天咨询"):
        st.session_state.mode = "智能对话"
        st.session_state.messages = []
        st.rerun()
with c4:
    if st.button("📄 简单文书模板"):
        st.session_state.mode = "文书生成"
        st.session_state.messages = []
        st.rerun()

st.info(f"当前模式：**{st.session_state.mode}**")

# 清空对话按钮
col1, col2 = st.columns([6, 1])
with col2:
    if st.button("🗑 清空对话"):
        st.session_state.messages = []
        st.rerun()

# 显示历史消息
for msg in st.session_state.messages:
    if msg["role"] in ["user", "assistant"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# 输入框
prompt = st.chat_input("随便问，用大白话回答你")

if prompt:
    # 添加用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 系统提示词
    system_prompt = {
        "通俗解答": "你是专业法律科普助手，要用超级大白话解释法律，不许用专业术语。别人怎么通俗问，你就怎么通俗答。不要讲法条编号，不要讲难懂词汇，像聊天一样回答。说人话，说简单话，说清楚话。",
        "节点提醒": "你是案件流程专家，用最简单的话讲流程、时间、步骤。分点说清楚，不要复杂，不要专业词。让普通人一眼看懂什么时候该做什么。",
        "智能对话": "你是贴心法律顾问，别人怎么说你就怎么回。完全口语化，不生硬，不官方，不摆架子。不懂的地方你主动用简单话解释清楚。",
        "文书生成": "你是法律文书助手，生成简单、实用、普通人能直接用的文书模板。结构清晰，内容简单，去掉复杂格式，直接能用。"
    }[st.session_state.mode]

    with st.chat_message("assistant"):
        with st.spinner("正在用大白话思考..."):
            try:
                # 调用API，传入完整历史消息
                res = st.session_state.hy_client.chat_with_history(
                    st.session_state.messages,
                    system_prompt
                )
                st.markdown(res)
                st.session_state.messages.append({"role": "assistant", "content": res})
            except Exception as e:
                err = f"请求失败：{str(e)}"
                st.error(err)
                # 不把错误消息加入历史，避免污染对话格式
