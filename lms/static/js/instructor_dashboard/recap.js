/* globals _ */

(function(_) {
    'use strict';

    var Recap = (function() {

       function RecapBlock($section) {
            this.$section = $section;
            this.$section.data('wrapper', this);
        }

        RecapBlock.prototype.onClickTitle = function() {
            var block = this.$section.find('.recap');
            XBlock.initializeBlock($(block).find('.xblock')[0]);
        };

        return RecapBlock;
    }());

    if (typeof window.setup_debug === 'undefined') {
        // eslint-disable-next-line no-unused-vars, camelcase
        window.setup_debug = function(element_id, edit_link, staff_context) {
            // stub function.
        };
    }

    _.defaults(window, {
        InstructorDashboard: {}
    });

    _.defaults(window.InstructorDashboard, {
        sections: {}
    });

    _.defaults(window.InstructorDashboard.sections, {
        Recap: Recap
    });

    this.Recap = Recap;
}).call(this, _);
