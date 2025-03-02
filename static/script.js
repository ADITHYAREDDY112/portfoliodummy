document.addEventListener("DOMContentLoaded", function () {
    calculateTotalValue();
    setupSellHandlers();
});

function calculateTotalValue() {
    let total = 0;
    const valueElements = document.querySelectorAll(".stock-value");

    valueElements.forEach(element => {
        total += parseFloat(element.textContent.replace("₹", "")) || 0; 
    });

    document.getElementById("total-value").textContent = total.toFixed(2);
}

function setupSellHandlers() {
    document.querySelectorAll(".sell-form").forEach(form => {
        form.addEventListener("submit", function (event) {
            event.preventDefault();

            const formData = new FormData(form);
            const stockId = form.dataset.stockId;
            const sellPrice = parseFloat(formData.get("sell_price"));
            const shares = parseInt(formData.get("shares"));
            const purchasePrice = parseFloat(form.dataset.purchasePrice);

            if (isNaN(sellPrice) || isNaN(shares) || sellPrice <= 0 || shares <= 0) {
                alert("Please enter a valid selling price and number of shares.");
                return;
            }

            fetch(`/sell_stock/${stockId}`, {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: new URLSearchParams({ shares, sell_price: sellPrice })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const totalPurchaseValue = purchasePrice * shares;
                    const totalSellValue = sellPrice * shares;
                    const profitLoss = totalSellValue - totalPurchaseValue;

                    alert(`Stock sold!\nProfit/Loss: ₹${profitLoss.toFixed(2)}`);

                    
                    const row = form.closest("tr");
                    row.classList.add("striked-out");

                    
                    setTimeout(() => {
                        row.remove();
                        calculateTotalValue(); 
                    }, 1000);
                } else {
                    alert("Error selling stock. Try again.");
                }
            })
            .catch(error => {
                console.error("Error:", error);
                alert("Error processing the request.");
            });
        });
    });
}
