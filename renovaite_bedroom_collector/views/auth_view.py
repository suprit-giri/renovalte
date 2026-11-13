# Authentication View (Login & Registration)
"""
User-friendly Login and Registration interfaces for RenovAIte Germany.
Manages user onboarding, credential verification, and routing to personal dashboard.
"""

import streamlit as st
from services.auth_service import login_user, register_user


def render_auth_view():
    """Renders the combined Login and Registration view."""
    # Outer layout to center the auth card
    _, center_col, _ = st.columns([1, 1.8, 1])

    with center_col:
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 25px;">
                <h1 style="font-size: 2.3rem; font-weight: 700; margin-bottom: 6px;">
                    RenovAIte Germany
                </h1>
                <p style="color: gray; font-size: 1.05rem; margin-top: 0;">
                    AI Digital Twin Platform for Residential Modernization
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        tab_login, tab_register = st.tabs(["🔐 Existing User — Log In", "✨ New User — Register"])

        # -----------------------------
        # Tab 1: Login
        # -----------------------------
        with tab_login:
            st.markdown("### Welcome Back")
            st.caption("Log in to access your personal bedroom renovation projects.")

            with st.form("login_form", clear_on_submit=False):
                login_email = st.text_input("Email Address", key="login_email_input").strip()
                login_password = st.text_input("Password", type="password", key="login_pwd_input")

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                login_submitted = st.form_submit_button("🚀 Log In to Dashboard", type="primary", use_container_width=True)

            if login_submitted:
                if not login_email or not login_password:
                    st.error("Please enter both email and password.")
                else:
                    success, message, user_data = login_user(login_email, login_password)
                    if success and user_data:
                        st.session_state.authenticated_user = user_data
                        st.session_state.app_view = "dashboard"
                        st.success("Login successful! Redirecting to your dashboard...")
                        st.rerun()
                    else:
                        st.error(f"⚠️ {message}")

        # -----------------------------
        # Tab 2: Registration
        # -----------------------------
        with tab_register:
            st.markdown("### Create Your Account")
            st.caption("Register to build, customize, and manage your renovation digital twins.")

            with st.form("register_form", clear_on_submit=False):
                reg_name = st.text_input("Full Name *", key="reg_name_input").strip()
                reg_email = st.text_input("Email Address *", key="reg_email_input").strip()
                reg_password = st.text_input("Password (min. 6 characters) *", type="password", key="reg_pwd_input")
                reg_confirm_password = st.text_input("Confirm Password *", type="password", key="reg_confirm_pwd_input")

                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                reg_submitted = st.form_submit_button("🎉 Create Account & Get Started", type="primary", use_container_width=True)

            if reg_submitted:
                if not reg_name or not reg_email or not reg_password:
                    st.error("Please fill in all mandatory fields.")
                elif reg_password != reg_confirm_password:
                    st.error("Passwords do not match. Please re-enter your password.")
                else:
                    success, message, user_data = register_user(reg_name, reg_email, reg_password)
                    if success and user_data:
                        st.session_state.authenticated_user = user_data
                        st.session_state.app_view = "dashboard"
                        st.success("Account created successfully! Redirecting to your dashboard...")
                        st.rerun()
                    else:
                        st.error(f"⚠️ {message}")

