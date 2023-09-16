document.addEventListener("DOMContentLoaded", function () {
    refundModalProcess();
});

function refundModalProcess() {
    let modal = document.getElementById("modal-refund");
    let openBtns = document.querySelectorAll(".refund-btn");
    let closeBtns = modal.querySelectorAll(".close");
    let form = modal.querySelector('#refund-form');
    let paymentInput = form.querySelector('input[name="payment_id"]');
    openBtns.forEach((btn) => {
        btn.onclick = function () {
            let paymentId = this.getAttribute("paymentId");
            paymentInput.value = paymentId;
            modal.classList.add('show');
        };
    });
    closeBtns.forEach((span) => {
        span.onclick = function () {
            closeModal(modal, paymentInput);
        };
    });
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            closeModal(modal, paymentInput);
        }
    });

    window.onclick = function (event) {
        if (event.target === modal) {
            closeModal(modal, paymentInput);
        }
    };
}

function closeModal(modal, paymentInput) {
    modal.classList.remove('show');
    paymentInput.value = '';
}