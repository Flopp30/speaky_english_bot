document.addEventListener("DOMContentLoaded", function () {
    refundModalProcess();
    sendMessageModalProcess();
});

function refundModalProcess() {
    let modal = document.getElementById("modal-refund");
    let openBtns = document.querySelectorAll(".refund-btn");
    let closeBtns = modal.querySelectorAll(".close");
    let form = modal.querySelector('#refund-form');
    let paymentInput = form.querySelector('input[name="payment_id"]');
    openBtns.forEach((btn) => {
        btn.onclick = function () {
            paymentInput.value = this.getAttribute("paymentId");
            modal.classList.add('show');
        };
    });
    closeBtns.forEach((span) => {
        span.onclick = function () {
            closeModal(modal, [paymentInput]);
        };
    });
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeModal(modal, [paymentInput]);
        }
    });

    window.onclick = function (event) {
        if (event.target === modal) {
            closeModal(modal, [paymentInput]);
        }
    };
}

function closeModal(modal, inputs) {
    modal.classList.remove('show');
    inputs.forEach((input) => {
        input.value = '';
    });
}

function sendMessageModalProcess() {
    let modal = document.getElementById("modal-send-message");
    let openBtns = document.querySelectorAll(".send-msg-btn");
    let closeBtns = modal.querySelectorAll(".close");
    let form = modal.querySelector('#send-message-form');
    let userInput = form.querySelector('input[name="user_id"]');
    let withLinkSelect = form.querySelector('#id_with_link');
    let hiddenArea = form.querySelector('#hidden-area-id');
    withLinkSelect.addEventListener('change', function () {
        if (this.value === 'True') {
            hiddenArea.classList.remove('d-none');
        } else {
            hiddenArea.classList.add('d-none');
        }
    });
    openBtns.forEach((btn) => {
        btn.onclick = function () {
            userInput.value = this.getAttribute("userId");
            modal.classList.add('show');
        };
    });
    closeBtns.forEach((span) => {
        span.onclick = function () {
            closeModal(modal, [userInput]);
        };
    });
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeModal(modal, [userInput]);
        }
    });

    window.onclick = function (event) {
        if (event.target === modal) {
            closeModal(modal, [userInput]);
        }
    };
}