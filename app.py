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
            
            # 🔴 强制只保留 user 和 assistant，彻底删除 tool
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
    st.session_state.mode = "法律解释"

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

# ===================== 功能模式 =====================
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("📚 法律解释"):
        st.session_state.mode = "法律解释"
with c2:
    if st.button("⏰ 节点提醒"):
        st.session_state.mode = "节点提醒"
with c3:
    if st.button("💬 智能对话"):
        st.session_state.mode = "智能对话"
with c4:
    if st.button("📄 文书生成"):
        st.session_state.mode = "文书生成"

st.info(f"当前模式：**{st.session_state.mode}**")

# 清空对话
if st.button("🗑 清空对话"):
    st.session_state.messages = []
    st.rerun()

# 显示历史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 输入框
prompt = st.chat_input("请输入您的问题")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    system_prompt = {
        "法律解释": "你是专业法律科普助手，通俗易懂解读法条，给出实用建议",
        "节点提醒": "分析案件流程节点、时效、重要提醒，清晰明了",
        "智能对话": "用通俗语言解答法律问题，少用专业术语",
        "文书生成": "生成规范、严谨的标准法律文书"
    }[st.session_state.mode]

    with st.chat_message("assistant"):
        with st.spinner("AI思考中..."):
            try:
                # 🔴 关键修复：过滤非法角色，只传合法消息
                clean_history = [
                    m for m in st.session_state.messages[:-1]
                    if m["role"] in ["user", "assistant"]
                ]
                
                res = st.session_state.hy_client.chat_with_history(
                    clean_history, system_prompt
                )
                st.markdown(res)
                st.session_state.messages.append({"role": "assistant", "content": res})
            except Exception as e:
                err = f"请求失败：{str(e)}"
                st.error(err)
                st.session_state.messages.append({"role": "assistant", "content": err})
