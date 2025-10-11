document.addEventListener('DOMContentLoaded', function() {
    // Add scroll event for header
    window.addEventListener('scroll', function() {
        const header = document.querySelector('.header');
        if (window.scrollY > 100) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    });
    
    // Hero slider functionality
    const slides = document.querySelectorAll('.hero-slide');
    const dots = document.querySelectorAll('.hero-dot');
    let currentSlide = 0;
    
    function showSlide(index) {
        slides.forEach(slide => slide.classList.remove('active'));
        dots.forEach(dot => dot.style.backgroundColor = '#ccc');
        dots.forEach(dot => dot.style.opacity = '0.5');
        
        slides[index].classList.add('active');
        dots[index].style.backgroundColor = 'var(--royal-gold)';
        dots[index].style.opacity = '1';
    }
    
    // Initialize automatic slider
    let slideInterval = setInterval(() => {
        currentSlide = (currentSlide + 1) % slides.length;
        showSlide(currentSlide);
    }, 5000);
    
    // Click events for dots
    dots.forEach((dot, index) => {
        dot.addEventListener('click', () => {
            clearInterval(slideInterval);
            currentSlide = index;
            showSlide(currentSlide);
            
            // Restart the interval
            slideInterval = setInterval(() => {
                currentSlide = (currentSlide + 1) % slides.length;
                showSlide(currentSlide);
            }, 5000);
        });
    });
    
    // Search toggle
    const searchToggle = document.getElementById('search-toggle');
    const searchContainer = document.querySelector('.search-form-container');
    
    if (searchToggle && searchContainer) {
        searchToggle.addEventListener('click', function() {
            searchContainer.classList.toggle('active');
        });
        
        // Close search when clicking outside
        document.addEventListener('click', function(event) {
            if (!event.target.closest('#search-toggle') && !event.target.closest('.search-form-container')) {
                searchContainer.classList.remove('active');
            }
        });
    }
    
    // Product card hover effect
    const productCards = document.querySelectorAll('[style*="background-color: white; border-radius: 12px; overflow: hidden; box-shadow"]');
    if (productCards) {
        productCards.forEach(card => {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-10px)';
                this.style.boxShadow = '0 20px 40px rgba(0,0,0,0.1)';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '0 15px 30px rgba(0,0,0,0.06)';
            });
        });
    }
    
    // Smooth scroll for anchor links - DISABLED to prevent navigation interference
    // Removed to allow normal navigation to work properly
});
