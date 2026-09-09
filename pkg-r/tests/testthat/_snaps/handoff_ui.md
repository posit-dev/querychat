# handoff_panel_ui() / renders the closed namespaced panel controls and editor

    Code
      cat(markup)
    Output
      <div id="module-handoff_root" class="querychat-handoff-root">
        <div class="querychat-handoff-backdrop"></div>
        <div class="querychat-handoff-panel">
          <div class="querychat-handoff-panel-header">
            <div class="querychat-handoff-title">
              <h3>Handoff</h3>
              <span class="querychat-handoff-header-spinner"></span>
            </div>
            <div class="querychat-handoff-header-spacer"></div>
            <button class="btn btn-sm querychat-handoff-icon-btn querychat-handoff-revise-toggle" type="button" title="Revise with AI" aria-label="Revise with AI"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-pencil-square " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M15.502 1.94a.5.5 0 0 1 0 .706L14.459 3.69l-2-2L13.502.646a.5.5 0 0 1 .707 0l1.293 1.293zm-1.75 2.456-2-2L4.939 9.21a.5.5 0 0 0-.121.196l-.805 2.414a.25.25 0 0 0 .316.316l2.414-.805a.5.5 0 0 0 .196-.12l6.813-6.814z"></path>
      <path fill-rule="evenodd" d="M1 13.5A1.5 1.5 0 0 0 2.5 15h11a1.5 1.5 0 0 0 1.5-1.5v-6a.5.5 0 0 0-1 0v6a.5.5 0 0 1-.5.5h-11a.5.5 0 0 1-.5-.5v-11a.5.5 0 0 1 .5-.5H9a.5.5 0 0 0 0-1H2.5A1.5 1.5 0 0 0 1 2.5v11z"></path></svg></button>
            <a aria-disabled="true" aria-label="Download" class="btn btn-default shiny-download-link disabled btn btn-sm querychat-handoff-icon-btn querychat-handoff-download-btn" download href="" id="module-handoff_download" tabindex="-1" target="_blank" title="Download"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-download " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"></path>
      <path d="M7.646 11.854a.5.5 0 0 0 .708 0l3-3a.5.5 0 0 0-.708-.708L8.5 10.293V1.5a.5.5 0 0 0-1 0v8.793L5.354 8.146a.5.5 0 1 0-.708.708l3 3z"></path></svg></a>
            <span class="querychat-handoff-header-divider"></span>
            <button aria-label="Close" class="btn btn-default action-button btn btn-sm querychat-handoff-icon-btn" id="module-handoff_close" title="Close" type="button"><span class="action-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-x-lg " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M2.146 2.854a.5.5 0 1 1 .708-.708L8 7.293l5.146-5.147a.5.5 0 0 1 .708.708L8.707 8l5.147 5.146a.5.5 0 0 1-.708.708L8 8.707l-5.146 5.147a.5.5 0 0 1-.708-.708L7.293 8 2.146 2.854Z"></path></svg></span></button>
          </div>
          <div class="querychat-handoff-revise-drawer">
            <div class="bslib-input-submit-textarea shiny-input-container bslib-mb-spacing" style="width:100%;">
              <label class="control-label shiny-label-null" for="module-handoff_revise_text" id="module-handoff_revise_text-label"></label>
              <div class="bslib-submit-textarea-container">
                <textarea id="module-handoff_revise_text" class="form-control" style="width:100%;" placeholder="Ask AI to revise this handoff." rows="1"></textarea>
                <footer>
                  <div class="bslib-toolbar"></div>
                  <button aria-label="Press Enter to Submit" class="btn btn-primary bslib-task-button btn-sm bslib-submit-textarea-btn" data-auto-reset id="module-handoff_revise_text_submit" title="Press Enter to Submit" type="button">
                    <bslib-switch-inline case="ready">
                      <span slot="ready">
                        Submit
                        <span class="bslib-submit-key">⏎</span>
                      </span>
                      <span slot="busy">
                        Submit
                        <div class="spinner-border spinner-border-sm ms-2" role="status">
                          <span class="visually-hidden">Processing...</span>
                        </div>
                      </span>
                    </bslib-switch-inline>
                  </button>
                </footer>
              </div>
            </div>
          </div>
          <div class="querychat-handoff-panel-error" style="display:none"></div>
          <div class="querychat-handoff-panel-body">
            <bslib-code-editor class="html-fill-container html-fill-item" data-require-bs-caller="input_code_editor()" data-require-bs-version="5" id="module-handoff_source_editor" insert-spaces="true" language="plain" line-numbers="false" readonly="true" style="height:auto;width:100%;" tab-size="2" theme-dark="github-dark" theme-light="github-light" value="" word-wrap="true">
              <label class="control-label shiny-label-null" for="module-handoff_source_editor" id="module-handoff_source_editor-label"></label>
              <div class="code-editor html-fill-item" style="display:grid;"></div>
            </bslib-code-editor>
          </div>
        </div>
      </div>

# handoff_modal_ui() / renders the empty gallery and namespaced language group

    Code
      cat(markup)
    Output
      <div class="modal fade" id="shiny-modal" tabindex="-1">
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h4 class="modal-title">Prepare Handoff</h4>
            </div>
            <div class="modal-body querychat-handoff-modal" id="module-handoff_modal_root">
              <p class="querychat-handoff-modal-intro">Preserve important findings in a standalone report, dashboard, or script.</p>
              <div class="querychat-handoff-section-label">
                Results to include
                <bslib-tooltip placement="top" bsOptions="[]" data-require-bs-version="5" data-require-bs-caller="tooltip()">
                  <template>Select which queries and visualizations to include in the handoff.</template>
                  <span class="querychat-handoff-info-icon" tabindex="0" aria-label="More information"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-info-circle " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"></path>
      <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"></path></svg></span>
                </bslib-tooltip>
              </div>
              <div class="querychat-handoff-loading-status hidden">
                <div class="spinner"></div>
                Analyzing your results...
              </div>
              <div class="querychat-handoff-gallery-scroll">
                <div class="querychat-handoff-gallery-empty">
                  <p>No results yet — ask a question first to populate the gallery.</p>
                </div>
              </div>
              <div class="querychat-handoff-section-label mt-2">
                Output format
                <bslib-tooltip placement="top" bsOptions="[]" data-require-bs-version="5" data-require-bs-caller="tooltip()">
                  <template>Choose the file type for the generated handoff.</template>
                  <span class="querychat-handoff-info-icon" tabindex="0" aria-label="More information"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-info-circle " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"></path>
      <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"></path></svg></span>
                </bslib-tooltip>
              </div>
              <div class="querychat-handoff-type-selector">
                <button class="querychat-handoff-type-pill active" type="button" data-handoff-type="quarto-dashboard" data-languages="python,r">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-grid-1x2-fill " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M0 1a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1V1zm9 0a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1V1zm0 9a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1v-5z"></path></svg>
                   Quarto
                </button>
                <button class="querychat-handoff-type-pill" type="button" data-handoff-type="marimo-notebook" data-languages="python">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-journal-code " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path fill-rule="evenodd" d="M8.646 5.646a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-2 2a.5.5 0 0 1-.708-.708L10.293 8 8.646 6.354a.5.5 0 0 1 0-.708zm-1.292 0a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0 0 .708l2 2a.5.5 0 0 0 .708-.708L5.707 8l1.647-1.646a.5.5 0 0 0 0-.708z"></path>
      <path d="M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-1h1v1a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v1H1V2a2 2 0 0 1 2-2z"></path>
      <path d="M1 5v-.5a.5.5 0 0 1 1 0V5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1zm0 3v-.5a.5.5 0 0 1 1 0V8h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1zm0 3v-.5a.5.5 0 0 1 1 0v.5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1z"></path></svg>
                   Marimo
                </button>
                <button class="querychat-handoff-type-pill" type="button" data-handoff-type="shiny-app" data-languages="python,r">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-lightning-fill " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641l2.5-8.5z"></path></svg>
                   Shiny
                </button>
                <button class="querychat-handoff-type-pill" type="button" data-handoff-type="jupyter-notebook" data-languages="python,r">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-file-earmark-code " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5L14 4.5zm-3 0A1.5 1.5 0 0 1 9.5 3V1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V4.5h-2z"></path>
      <path d="M8.646 6.646a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-2 2a.5.5 0 0 1-.708-.708L10.293 9 8.646 7.354a.5.5 0 0 1 0-.708zm-1.292 0a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0 0 .708l2 2a.5.5 0 0 0 .708-.708L5.707 9l1.647-1.646a.5.5 0 0 0 0-.708z"></path></svg>
                   Jupyter
                </button>
                <button class="querychat-handoff-type-pill" type="button" data-handoff-type="other" data-languages="python,r">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-three-dots " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M3 9.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm5 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm5 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3z"></path></svg>
                   Other
                </button>
              </div>
              <div class="querychat-handoff-freeform-input hidden">
                <input type="text" class="form-control mt-2" placeholder="e.g., R Markdown report, Streamlit app, SQL script..."/>
              </div>
              <div class="querychat-handoff-section-label mt-2">
                Language
                <bslib-tooltip placement="top" bsOptions="[]" data-require-bs-version="5" data-require-bs-caller="tooltip()">
                  <template>Preferred programming language. Quarto, Shiny, and Jupyter support either R or Python; Marimo is Python only.</template>
                  <span class="querychat-handoff-info-icon" tabindex="0" aria-label="More information"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-info-circle " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"></path>
      <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"></path></svg></span>
                </bslib-tooltip>
              </div>
              <div class="querychat-handoff-language-selector" role="radiogroup" aria-label="Programming language">
                <label class="querychat-handoff-language-option querychat-handoff-language-pill" data-language="python">
                  <input type="radio" name="module-handoff_language" class="querychat-handoff-language-radio" data-language="python" checked=""/>
                  <span class="querychat-handoff-language-icon querychat-handoff-language-icon-python"></span>
                  Python
                </label>
                <label class="querychat-handoff-language-option querychat-handoff-language-pill" data-language="r">
                  <input type="radio" name="module-handoff_language" class="querychat-handoff-language-radio" data-language="r"/>
                  <span class="querychat-handoff-language-icon querychat-handoff-language-icon-r"></span>
                  R
                </label>
              </div>
              <div class="querychat-handoff-section-label-row mt-2">
                <div class="querychat-handoff-section-label">
                  Generation notes
                  <bslib-tooltip placement="top" bsOptions="[]" data-require-bs-version="5" data-require-bs-caller="tooltip()">
                    <template>Optional instructions for the AI on how to structure or style the handoff.</template>
                    <span class="querychat-handoff-info-icon" tabindex="0" aria-label="More information"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-info-circle " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"></path>
      <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"></path></svg></span>
                  </bslib-tooltip>
                </div>
                <span class="querychat-handoff-directions-subtitle hidden">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-stars " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M7.657 6.247c.11-.33.576-.33.686 0l.645 1.937a2.89 2.89 0 0 0 1.829 1.828l1.936.645c.33.11.33.576 0 .686l-1.937.645a2.89 2.89 0 0 0-1.828 1.829l-.645 1.936a.361.361 0 0 1-.686 0l-.645-1.937a2.89 2.89 0 0 0-1.828-1.828l-1.937-.645a.361.361 0 0 1 0-.686l1.937-.645a2.89 2.89 0 0 0 1.828-1.828l.645-1.937zM3.794 1.148a.217.217 0 0 1 .412 0l.387 1.162c.173.518.579.924 1.097 1.097l1.162.387a.217.217 0 0 1 0 .412l-1.162.387A1.734 1.734 0 0 0 4.593 5.69l-.387 1.162a.217.217 0 0 1-.412 0L3.407 5.69A1.734 1.734 0 0 0 2.31 4.593l-1.162-.387a.217.217 0 0 1 0-.412l1.162-.387A1.734 1.734 0 0 0 3.407 2.31l.387-1.162zM10.863.099a.145.145 0 0 1 .274 0l.258.774c.115.346.386.617.732.732l.774.258a.145.145 0 0 1 0 .274l-.774.258a1.156 1.156 0 0 0-.732.732l-.258.774a.145.145 0 0 1-.274 0l-.258-.774a1.156 1.156 0 0 0-.732-.732L9.1 2.137a.145.145 0 0 1 0-.274l.774-.258c.346-.115.617-.386.732-.732L10.863.1z"></path></svg>
                  Pre-filled by AI
                </span>
              </div>
              <div class="querychat-handoff-directions-wrapper">
                <div class="shiny-input-textarea form-group shiny-input-container" style="width:100%;">
                  <label class="control-label shiny-label-null" for="module-handoff_directions" id="module-handoff_directions-label"></label>
                  <textarea id="module-handoff_directions" class="form-control textarea-autoresize" placeholder="e.g., Use a dark theme, put the revenue chart prominently..." style="width:100%;" rows="1" data-update-on="change"></textarea>
                </div>
              </div>
              <div class="d-flex justify-content-end mt-2">
                <button id="module-handoff_generate" class="btn btn-primary querychat-handoff-generate" disabled="disabled">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-stars " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M7.657 6.247c.11-.33.576-.33.686 0l.645 1.937a2.89 2.89 0 0 0 1.829 1.828l1.936.645c.33.11.33.576 0 .686l-1.937.645a2.89 2.89 0 0 0-1.828 1.829l-.645 1.936a.361.361 0 0 1-.686 0l-.645-1.937a2.89 2.89 0 0 0-1.828-1.828l-1.937-.645a.361.361 0 0 1 0-.686l1.937-.645a2.89 2.89 0 0 0 1.828-1.828l.645-1.937zM3.794 1.148a.217.217 0 0 1 .412 0l.387 1.162c.173.518.579.924 1.097 1.097l1.162.387a.217.217 0 0 1 0 .412l-1.162.387A1.734 1.734 0 0 0 4.593 5.69l-.387 1.162a.217.217 0 0 1-.412 0L3.407 5.69A1.734 1.734 0 0 0 2.31 4.593l-1.162-.387a.217.217 0 0 1 0-.412l1.162-.387A1.734 1.734 0 0 0 3.407 2.31l.387-1.162zM10.863.099a.145.145 0 0 1 .274 0l.258.774c.115.346.386.617.732.732l.774.258a.145.145 0 0 1 0 .274l-.774.258a1.156 1.156 0 0 0-.732.732l-.258.774a.145.145 0 0 1-.274 0l-.258-.774a1.156 1.156 0 0 0-.732-.732L9.1 2.137a.145.145 0 0 1 0-.274l.774-.258c.346-.115.617-.386.732-.732L10.863.1z"></path></svg>
                   Generate
                </button>
              </div>
            </div>
          </div>
        </div>
        <script>if (window.bootstrap && !window.bootstrap.Modal.VERSION.match(/^4\./)) {
               var modal = new bootstrap.Modal(document.getElementById('shiny-modal'));
               modal.show();
            } else {
               $('#shiny-modal').modal().focus();
            }</script>
      </div>

# handoff_modal_ui() / renders gallery item attributes and escapes their titles

    Code
      cat(markup)
    Output
      <div class="modal fade" id="shiny-modal" tabindex="-1">
        <div class="modal-dialog modal-lg">
          <div class="modal-content">
            <div class="modal-header">
              <h4 class="modal-title">Prepare Handoff</h4>
            </div>
            <div class="modal-body querychat-handoff-modal" id="module-handoff_modal_root">
              <p class="querychat-handoff-modal-intro">Preserve important findings in a standalone report, dashboard, or script.</p>
              <div class="querychat-handoff-section-label">
                Results to include
                <bslib-tooltip placement="top" bsOptions="[]" data-require-bs-version="5" data-require-bs-caller="tooltip()">
                  <template>Select which queries and visualizations to include in the handoff.</template>
                  <span class="querychat-handoff-info-icon" tabindex="0" aria-label="More information"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-info-circle " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"></path>
      <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"></path></svg></span>
                </bslib-tooltip>
              </div>
              <div class="querychat-handoff-loading-status">
                <div class="spinner"></div>
                Analyzing your results...
              </div>
              <div class="querychat-handoff-gallery-scroll">
                <div class="querychat-handoff-gallery loading">
                  <div class="querychat-handoff-gallery-item" data-item-id="query-0">
                    <div class="gallery-checkbox">
                      <svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
                        <polyline points="3 6.5 5.5 9 9 3.5"></polyline>
                      </svg>
                    </div>
                    <div class="preview-container">
                      <div class="sql-snippet">SELECT 1</div>
                    </div>
                    <div class="title">&lt;script&gt;alert("x")&lt;/script&gt; &amp; report</div>
                  </div>
                  <div class="querychat-handoff-gallery-item" data-item-id="viz-1">
                    <div class="gallery-checkbox">
                      <svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
                        <polyline points="3 6.5 5.5 9 9 3.5"></polyline>
                      </svg>
                    </div>
                    <div class="preview-container">
                      <img src="data:image/png;base64,abc" alt="&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; report" draggable="false"/>
                    </div>
                    <div class="title">&lt;script&gt;alert("x")&lt;/script&gt; &amp; report</div>
                  </div>
                </div>
              </div>
              <div class="querychat-handoff-section-label mt-2">
                Output format
                <bslib-tooltip placement="top" bsOptions="[]" data-require-bs-version="5" data-require-bs-caller="tooltip()">
                  <template>Choose the file type for the generated handoff.</template>
                  <span class="querychat-handoff-info-icon" tabindex="0" aria-label="More information"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-info-circle " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"></path>
      <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"></path></svg></span>
                </bslib-tooltip>
              </div>
              <div class="querychat-handoff-type-selector">
                <button class="querychat-handoff-type-pill active" type="button" data-handoff-type="quarto-dashboard" data-languages="python,r">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-grid-1x2-fill " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M0 1a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H1a1 1 0 0 1-1-1V1zm9 0a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1V1zm0 9a1 1 0 0 1 1-1h5a1 1 0 0 1 1 1v5a1 1 0 0 1-1 1h-5a1 1 0 0 1-1-1v-5z"></path></svg>
                   Quarto
                </button>
                <button class="querychat-handoff-type-pill" type="button" data-handoff-type="marimo-notebook" data-languages="python">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-journal-code " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path fill-rule="evenodd" d="M8.646 5.646a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-2 2a.5.5 0 0 1-.708-.708L10.293 8 8.646 6.354a.5.5 0 0 1 0-.708zm-1.292 0a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0 0 .708l2 2a.5.5 0 0 0 .708-.708L5.707 8l1.647-1.646a.5.5 0 0 0 0-.708z"></path>
      <path d="M3 0h10a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2v-1h1v1a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V2a1 1 0 0 0-1-1H3a1 1 0 0 0-1 1v1H1V2a2 2 0 0 1 2-2z"></path>
      <path d="M1 5v-.5a.5.5 0 0 1 1 0V5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1zm0 3v-.5a.5.5 0 0 1 1 0V8h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1zm0 3v-.5a.5.5 0 0 1 1 0v.5h.5a.5.5 0 0 1 0 1h-2a.5.5 0 0 1 0-1H1z"></path></svg>
                   Marimo
                </button>
                <button class="querychat-handoff-type-pill" type="button" data-handoff-type="shiny-app" data-languages="python,r">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-lightning-fill " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M5.52.359A.5.5 0 0 1 6 0h4a.5.5 0 0 1 .474.658L8.694 6H12.5a.5.5 0 0 1 .395.807l-7 9a.5.5 0 0 1-.873-.454L6.823 9.5H3.5a.5.5 0 0 1-.48-.641l2.5-8.5z"></path></svg>
                   Shiny
                </button>
                <button class="querychat-handoff-type-pill" type="button" data-handoff-type="jupyter-notebook" data-languages="python,r">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-file-earmark-code " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5L14 4.5zm-3 0A1.5 1.5 0 0 1 9.5 3V1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V4.5h-2z"></path>
      <path d="M8.646 6.646a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-2 2a.5.5 0 0 1-.708-.708L10.293 9 8.646 7.354a.5.5 0 0 1 0-.708zm-1.292 0a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0 0 .708l2 2a.5.5 0 0 0 .708-.708L5.707 9l1.647-1.646a.5.5 0 0 0 0-.708z"></path></svg>
                   Jupyter
                </button>
                <button class="querychat-handoff-type-pill" type="button" data-handoff-type="other" data-languages="python,r">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-three-dots " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M3 9.5a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm5 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm5 0a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3z"></path></svg>
                   Other
                </button>
              </div>
              <div class="querychat-handoff-freeform-input hidden">
                <input type="text" class="form-control mt-2" placeholder="e.g., R Markdown report, Streamlit app, SQL script..."/>
              </div>
              <div class="querychat-handoff-section-label mt-2">
                Language
                <bslib-tooltip placement="top" bsOptions="[]" data-require-bs-version="5" data-require-bs-caller="tooltip()">
                  <template>Preferred programming language. Quarto, Shiny, and Jupyter support either R or Python; Marimo is Python only.</template>
                  <span class="querychat-handoff-info-icon" tabindex="0" aria-label="More information"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-info-circle " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"></path>
      <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"></path></svg></span>
                </bslib-tooltip>
              </div>
              <div class="querychat-handoff-language-selector" role="radiogroup" aria-label="Programming language">
                <label class="querychat-handoff-language-option querychat-handoff-language-pill" data-language="python">
                  <input type="radio" name="module-handoff_language" class="querychat-handoff-language-radio" data-language="python" checked=""/>
                  <span class="querychat-handoff-language-icon querychat-handoff-language-icon-python"></span>
                  Python
                </label>
                <label class="querychat-handoff-language-option querychat-handoff-language-pill" data-language="r">
                  <input type="radio" name="module-handoff_language" class="querychat-handoff-language-radio" data-language="r"/>
                  <span class="querychat-handoff-language-icon querychat-handoff-language-icon-r"></span>
                  R
                </label>
              </div>
              <div class="querychat-handoff-section-label-row mt-2">
                <div class="querychat-handoff-section-label">
                  Generation notes
                  <bslib-tooltip placement="top" bsOptions="[]" data-require-bs-version="5" data-require-bs-caller="tooltip()">
                    <template>Optional instructions for the AI on how to structure or style the handoff.</template>
                    <span class="querychat-handoff-info-icon" tabindex="0" aria-label="More information"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-info-circle " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z"></path>
      <path d="m8.93 6.588-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z"></path></svg></span>
                  </bslib-tooltip>
                </div>
                <span class="querychat-handoff-directions-subtitle hidden">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-stars " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M7.657 6.247c.11-.33.576-.33.686 0l.645 1.937a2.89 2.89 0 0 0 1.829 1.828l1.936.645c.33.11.33.576 0 .686l-1.937.645a2.89 2.89 0 0 0-1.828 1.829l-.645 1.936a.361.361 0 0 1-.686 0l-.645-1.937a2.89 2.89 0 0 0-1.828-1.828l-1.937-.645a.361.361 0 0 1 0-.686l1.937-.645a2.89 2.89 0 0 0 1.828-1.828l.645-1.937zM3.794 1.148a.217.217 0 0 1 .412 0l.387 1.162c.173.518.579.924 1.097 1.097l1.162.387a.217.217 0 0 1 0 .412l-1.162.387A1.734 1.734 0 0 0 4.593 5.69l-.387 1.162a.217.217 0 0 1-.412 0L3.407 5.69A1.734 1.734 0 0 0 2.31 4.593l-1.162-.387a.217.217 0 0 1 0-.412l1.162-.387A1.734 1.734 0 0 0 3.407 2.31l.387-1.162zM10.863.099a.145.145 0 0 1 .274 0l.258.774c.115.346.386.617.732.732l.774.258a.145.145 0 0 1 0 .274l-.774.258a1.156 1.156 0 0 0-.732.732l-.258.774a.145.145 0 0 1-.274 0l-.258-.774a1.156 1.156 0 0 0-.732-.732L9.1 2.137a.145.145 0 0 1 0-.274l.774-.258c.346-.115.617-.386.732-.732L10.863.1z"></path></svg>
                  Pre-filled by AI
                </span>
              </div>
              <div class="querychat-handoff-directions-wrapper loading">
                <div class="shiny-input-textarea form-group shiny-input-container" style="width:100%;">
                  <label class="control-label shiny-label-null" for="module-handoff_directions" id="module-handoff_directions-label"></label>
                  <textarea id="module-handoff_directions" class="form-control textarea-autoresize" placeholder="e.g., Use a dark theme, put the revenue chart prominently..." style="width:100%;" rows="1" data-update-on="change" disabled="disabled"></textarea>
                </div>
              </div>
              <div class="d-flex justify-content-end mt-2">
                <button id="module-handoff_generate" class="btn btn-primary querychat-handoff-generate" disabled="disabled">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-stars " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M7.657 6.247c.11-.33.576-.33.686 0l.645 1.937a2.89 2.89 0 0 0 1.829 1.828l1.936.645c.33.11.33.576 0 .686l-1.937.645a2.89 2.89 0 0 0-1.828 1.829l-.645 1.936a.361.361 0 0 1-.686 0l-.645-1.937a2.89 2.89 0 0 0-1.828-1.828l-1.937-.645a.361.361 0 0 1 0-.686l1.937-.645a2.89 2.89 0 0 0 1.828-1.828l.645-1.937zM3.794 1.148a.217.217 0 0 1 .412 0l.387 1.162c.173.518.579.924 1.097 1.097l1.162.387a.217.217 0 0 1 0 .412l-1.162.387A1.734 1.734 0 0 0 4.593 5.69l-.387 1.162a.217.217 0 0 1-.412 0L3.407 5.69A1.734 1.734 0 0 0 2.31 4.593l-1.162-.387a.217.217 0 0 1 0-.412l1.162-.387A1.734 1.734 0 0 0 3.407 2.31l.387-1.162zM10.863.099a.145.145 0 0 1 .274 0l.258.774c.115.346.386.617.732.732l.774.258a.145.145 0 0 1 0 .274l-.774.258a1.156 1.156 0 0 0-.732.732l-.258.774a.145.145 0 0 1-.274 0l-.258-.774a1.156 1.156 0 0 0-.732-.732L9.1 2.137a.145.145 0 0 1 0-.274l.774-.258c.346-.115.617-.386.732-.732L10.863.1z"></path></svg>
                   Generate
                </button>
              </div>
            </div>
          </div>
        </div>
        <script>if (window.bootstrap && !window.bootstrap.Modal.VERSION.match(/^4\./)) {
               var modal = new bootstrap.Modal(document.getElementById('shiny-modal'));
               modal.show();
            } else {
               $('#shiny-modal').modal().focus();
            }</script>
      </div>

# render_handoff_pill() / renders Python-compatible data attributes and escapes the label

    Code
      cat(markup)
    Output
      <button type="button" class="querychat-handoff-pill" data-handoff-id="handoff-123" data-input-id="module-handoff_open">
        <span class="querychat-handoff-pill-icon"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-file-earmark-code " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path d="M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5L14 4.5zm-3 0A1.5 1.5 0 0 1 9.5 3V1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V4.5h-2z"></path>
      <path d="M8.646 6.646a.5.5 0 0 1 .708 0l2 2a.5.5 0 0 1 0 .708l-2 2a.5.5 0 0 1-.708-.708L10.293 9 8.646 7.354a.5.5 0 0 1 0-.708zm-1.292 0a.5.5 0 0 0-.708 0l-2 2a.5.5 0 0 0 0 .708l2 2a.5.5 0 0 0 .708-.708L5.707 9l1.647-1.646a.5.5 0 0 0 0-.708z"></path></svg></span>
        <span class="querychat-handoff-pill-body">
          <span class="querychat-handoff-pill-title">Handoff</span>
          <span class="querychat-handoff-pill-subtitle">&lt;b&gt;R&lt;/b&gt; &amp; Co</span>
        </span>
        <span class="querychat-handoff-pill-open"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" class="bi bi-box-arrow-up-right " style="height:1em;width:1em;fill:currentColor;vertical-align:-0.125em;" aria-hidden="true" role="img" ><path fill-rule="evenodd" d="M8.636 3.5a.5.5 0 0 0-.5-.5H1.5A1.5 1.5 0 0 0 0 4.5v10A1.5 1.5 0 0 0 1.5 16h10a1.5 1.5 0 0 0 1.5-1.5V7.864a.5.5 0 0 0-1 0V14.5a.5.5 0 0 1-.5.5h-10a.5.5 0 0 1-.5-.5v-10a.5.5 0 0 1 .5-.5h6.636a.5.5 0 0 0 .5-.5z"></path>
      <path fill-rule="evenodd" d="M16 .5a.5.5 0 0 0-.5-.5h-5a.5.5 0 0 0 0 1h3.793L6.146 9.146a.5.5 0 1 0 .708.708L15 1.707V5.5a.5.5 0 0 0 1 0v-5z"></path></svg></span>
      </button>

