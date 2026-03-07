(function() {
    'use strict';
    
    // MOBILE RESTRICTION: no modals, admin side blocked on small screen
    function checkMobile() {
        // Make sure document.body exists
        if (!document.body) {
            console.log('⏳ Body not ready yet, will retry...');
            return;
        }
        
        const isMobile = window.innerWidth < 768; // match breakpoint
        console.log('📱 Mobile check:', { width: window.innerWidth, isMobile });
        
        if (isMobile) {
            document.body.classList.add('mobile-block-active');
            console.log('✅ Added mobile-block-active class');
        } else {
            document.body.classList.remove('mobile-block-active');
            console.log('❌ Removed mobile-block-active class');
        }
    }
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            console.log('📱 DOM loaded, running mobile check...');
            checkMobile();
        });
    } else {
        // DOM already loaded
        console.log('📱 DOM already loaded, running mobile check...');
        checkMobile();
    }
    
    // Listen to resize (with safety check)
    window.addEventListener('resize', function() {
        // Small delay to ensure everything is ready
        setTimeout(checkMobile, 10);
    });
    
    // Also check after page fully loads
    window.addEventListener('load', function() {
        console.log('📱 Page fully loaded, running mobile check...');
        checkMobile();
    });
})();