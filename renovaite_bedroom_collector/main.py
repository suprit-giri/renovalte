# Central Streamlit orchestrator & entry point
"""
Central orchestrator and Streamlit entry point for RenovAIte Germany.
Execute with: streamlit run main.py
"""

import streamlit as st
import streamlit.components.v1 as components
from state import init_session_state
from views import (
    render_auth_view,
    render_dashboard_view,
    render_top_navigation,
    render_bottom_navigation,
    render_step_1,
    render_step_2,
    render_step_3,
    render_step_4,
    render_step_5,
    render_step_6,
)


def main():
    st.set_page_config(
        page_title="RenovAIte Germany — Bedroom Renovation Intake",
        page_icon="🛏️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    init_session_state()

    # Hide the sidebar, tooltip icons, and manage top padding
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        [data-testid="stTooltipIcon"],
        .stTooltipIcon {
            display: none !important;
        }
        .block-container {
            padding-top: 3.5rem !important;
        }
        iframe[height="0"] {
            position: absolute !important;
            height: 0 !important;
            width: 0 !important;
            border: none !important;
            visibility: hidden !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # -------------------------------------------------------------
    # Application View Routing
    # -------------------------------------------------------------
    current_user = st.session_state.get("authenticated_user")

    # 1. Unauthenticated -> Always show Login / Registration
    if not current_user or st.session_state.app_view == "auth":
        render_auth_view()
        return

    # 2. Authenticated -> User Project Dashboard
    if st.session_state.app_view == "dashboard":
        render_dashboard_view()
        return

    # 3. Authenticated -> Project Creation Wizard
    if st.session_state.app_view == "create_project":
        # Reset scroll to top whenever moving across wizard sections
        if st.session_state.get("_last_rendered_step") != st.session_state.current_step:
            st.session_state._last_rendered_step = st.session_state.current_step
            components.html(
                """
                <script>
                    function doScroll() {
                        try {
                            const targets = [
                                window.parent.document.querySelector('.main'),
                                window.parent.document.querySelector('[data-testid="stMain"]'),
                                window.parent.document.querySelector('[data-testid="stAppViewContainer"]'),
                                window.parent.document.documentElement,
                                window.parent.document.body
                            ];
                            targets.forEach(function(el) {
                                if (el) el.scrollTop = 0;
                            });
                            if (window.parent) {
                                window.parent.scrollTo(0, 0);
                            }
                        } catch (e) {
                            console.error(e);
                        }
                    }
                    doScroll();
                    setTimeout(doScroll, 50);
                    setTimeout(doScroll, 150);
                </script>
                """,
                height=0,
                width=0,
            )

        # Centered Application Header
        st.markdown(
            """
            <div style="text-align: center; margin-top: 5px; margin-bottom: 20px;">
                <h1 style="font-size: 2.4rem; font-weight: 700; margin: 0;">
                    RenovAIte Germany
                </h1>
            </div>
            """,
            unsafe_allow_html=True,
        )

        render_top_navigation()

        if st.session_state.current_step == 1:
            render_step_1()
        elif st.session_state.current_step == 2:
            render_step_2()
        elif st.session_state.current_step == 3:
            render_step_3()
        elif st.session_state.current_step == 4:
            render_step_4()
        elif st.session_state.current_step == 5:
            render_step_5()
        elif st.session_state.current_step == 6:
            render_step_6()

        render_bottom_navigation()
        return

    # Fallback to dashboard
    st.session_state.app_view = "dashboard"
    render_dashboard_view()


if __name__ == "__main__":
    main()
