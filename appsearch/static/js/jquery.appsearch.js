// Depends on formset.js

(function($){
    $.fn.appsearch = function(opts){
        var options = $.extend({}, $.fn.appsearch.defaults, opts);
        var form = this;
        var _option_template = $("<option />")
        
        form.data('options', options);
        
        options.modelSelect.on('change.appsearch', function(){
            // Model has changed; trigger field list update
            var select = $(this);
            var value = select.val();
            if (value == '') {
                form.find('.constraint-form').slideUp('fast', function(){
                    $(this).find('.delete-row').click();
                })
            } else {
                form.trigger('update-field-list.appsearch');
            }
        });
        form.find('.constraint-field select').on('change.appsearch', function(){
            // Field has changed; trigger operator list update for the target constraint
            var constraintForm = $(this).closest('.constraint-form');
            form.trigger('update-operator-list', [constraintForm]);
        });
        form.find('.constraint-operator select').on('change.appsearch', function(){
            var select = $(this);
            var value = select.val();
            var termInputs = select.closest('.constraint-form').find('.term');
            
            if (options.termlessOperators.indexOf(value) != -1) {
                // termless operator; hide inputs
                termInputs.slideUp('fast');
            } else {
                if (options.twoTermOperators.indexOf(value) != -1) {
                    // two-term operator; show both inputs
                    termInputs.slideDown('fast');
                } else {
                    // one-term operator; hide second input
                    termInputs.filter('.begin-term').slideDown('fast');
                    termInputs.filter('.end-term').slideUp('fast');
                }
            }
        });
        
        form.on('update-field-list.appsearch', function(e){
            // Default handler that tries to call a user-supplied function or else the default one
            (options.updateFieldList || function(){
                var modelSelect = form.find('#model-select-wrapper select')
                var modelValue = modelSelect.val();
                var choices = (options.getFields || $.fn.appsearch._getFields)(form, modelValue);
                
                // Remove all constraint forms but the first one.
                var constraintForms = form.find('.constraint-form');
                constraintForms.slice(1).slideUp('fast', function(){
                    $(this).find('.delete-row').click(); // formset.js
                });
                
                // 1 or 0 remaining constraint-form divs; make sure 1 exists
                var constraintForm = constraintForms.eq(0);
                if (constraintForm.size() == 0) {
                    form.find('.add-row').click(); // formset.js
                    constraintForm = form.find('.constraint-form');
                }
                        
                // Set the field <option> choices
                var fieldSelect = constraintForm.find('.constraint-field select');
                fieldSelect.empty();
                for (var i = 0; i < choices.length; i++) {
                    var pair = choices[i];
                    fieldSelect.append(_option_template.clone().val(pair[0]).text(pair[1]));
                }
                
                // Ask for the operator list to update according to the form's field
                form.trigger('update-operator-list', [constraintForm]);
            })(e);
        });
        form.on('update-operator-list.appsearch', function(e, constraintForm){
            (options.updateOperatorList || function(e, constraintForm){
                var fieldSelect = constraintForm.find('.constraint-field select');
            
                var modelValue = options.modelSelect.val();
                var fieldValue = fieldSelect.val();
                var choices = (options.getOperators || $.fn.appsearch._getOperators)(form, modelValue, fieldValue);
            
                var operatorSelect = constraintForm.find('.constraint-operator select').empty();
                for (var i = 0; i < choices.length; i++) {
                    operatorSelect.append(_option_template.clone().val(choices[i]).text(choices[i]));
                }
                
                // Propagate change through the operator <select>
                operatorSelect.change();
                    
                form.trigger('constraint-form-changed', [constraintForm]);
            })(e, constraintForm);
        });
        form.on('constraint-form-changed', function(e, constraintForm){
            (options.constraintFormChanged || function(e, constraintForm){
                // Re-initialize the formset after stripping out the add/remove links
                form.find('.add-row,.delete-row').remove(); // formset.js
                form.find('.constraint-form').formset(options.formsetOptions); // formset.js
            });
        });
    
        // Make the form available for chained calls
        return this;
    };
    
    $.fn.appsearch._getFields = function(form, modelValue){
        var choices = null;
        $.ajax(form.data('options').constraintFieldDataURL, {
            data: {'model': modelValue},
            async: false,
            success: function(response){ choices = response.choices; },
            error: function(){ choices = []; }
        });
        
        return choices;
    };
    
    $.fn.appsearch._getOperators = function(form, modelValue, fieldValue){
        var choices = null;
        $.ajax(form.data('options').constraintOperatorDataURL, {
            data: {'model': modelValue, 'field': fieldValue},
            async: false,
            success: function(response){ choices = response.choices; },
            error: function(){ choices = []; }
        });
        
        return choices;
    };
    
    $.fn.appsearch.defaults = {
        'constraintFieldDataURL': null,
        'constraintOperatorDataURL': null,
        'modelSelect': null,
        
        'modelSelectedCallback': null,
        'updateFieldList': null,
        'updateOperatorList': null,
        'constraintFormChanged': null,
        
        'getFields': null,
        'getOperators': null,
        
        'termlessOperators': ["exists", "doesn't exist"],
        'twoTermOperators': ["range"],
        
        'formsetOptions': null,
    };
})(jQuery);
