(function(){
    var formUrl = $('#run_variables').attr('action');

    var previewScript = function previewScript(event){
        var submitAction = function submitAction(){
            var url = $('#preview_url').val();
            var $form = $('#run_variables');
            if($form.length===0) $form = $('#instrument_variables');
            $form.attr('action', url);

            $('.js-script-container').text('');
            $('#script-preview-modal .progress').show();
            $('#script-preview-modal').modal();
            $.ajax({
                type: "POST",
                url: url,
                data: $form.serialize(),
                success: function(data) {
                    $('.js-script-container').removeClass('prettyprinted').text(data);
                    prettyPrint();
                    $('#script-preview-modal .progress').hide();
                }
            });
        };
        var cancelAction = function cancelAction(){
            return false;
        };

        event.preventDefault();
        if(validateForm()){
            submitAction();
        }else{
            cancelAction();
        }
    };

    var downloadScript  = function downloadScript(event){
        var submitAction = function submitAction(){
            var url = $('#preview_url').val();
            var $form = $('#run_variables');
            if($form.length===0) $form = $('#instrument_variables');
            $form.attr('action', url);
            window.onbeforeunload = undefined;
            $form.submit();
        };
        var cancelAction = function cancelAction(){
            return false;
        };
        event.preventDefault();
        if(validateForm()){
            submitAction();
        }else{
            cancelAction();
        }
    };

    var validateForm = function validateForm(){
        var isValid = true;
        var errorMessages = [];
        var $errorList;
        var $form = $('#run_variables');
        if($form.length===0) $form = $('#instrument_variables');

        var resetValidationStates = function resetValidationStates(){
            $('.has-error').removeClass('has-error');
            $('.js-form-validation-message').hide();
        };

        var getVarName = function getVarName($input){
            return '<strong>' + $input.attr('id').replace('var-standard-','').replace('var-advanced-','').replace('-',' ') + '</strong>';
        };

        var validateRunRange = function validateRunRange(){
            var $start = $('#run_start');
            var $end = $('#run_end');
            var $experiment_reference = $('#experiment_reference');
            if($start.length && $end.length && $experiment_reference.length){
                if($('#variable-range-toggle').length >0 && !$('#variable-range-toggle').bootstrapSwitch('state')){
                    validateNotEmpty.call($experiment_reference[0]);
                    if(!isNumber($experiment_reference.val())){
                        $experiment_reference.parent().addClass('has-error');
                        isValid = false;
                        errorMessages.push('<strong>Experiment Reference Number</strong> must be a number.')
                    }
                }else{
                    validateNotEmpty.call($start[0]);
                    if(!isNumber($start.val())){
                        $start.parent().addClass('has-error');
                        isValid = false;
                        errorMessages.push('<strong>Run start</strong> must be a number.')
                    }
                    if($end.val() !== '' && !isNumber($end.val())){
                        $end.parent().addClass('has-error');
                        isValid = false;
                        errorMessages.push('<strong>Run finish</strong> can only be a number.')
                    }
                    if(parseInt($end.val()) < parseInt($start.val())){
                        $end.parent().addClass('has-error');
                        isValid = false;
                        errorMessages.push('<strong>Run finish</strong> must be greater than the run start.')
                    }
                }
            }
        };

        var validateNotEmpty = function validateNotEmpty(){
            
            if($(this).val().trim() === ''){
                $(this).parent().addClass('has-error');
                isValid = false;
                errorMessages.push(getVarName($(this)) + ' is required.')
            }
        };
        var validateText = function validateText(){
            validateNotEmpty.call(this);
        };
        var validateNumber = function validateNumber(){
            validateNotEmpty.call(this);
            if(!isNumber($(this).val())){
                $(this).parent().addClass('has-error');
                isValid = false;
                errorMessages.push(getVarName($(this)) + ' must be a number.')
            }
        };
        var validateBoolean = function validateBoolean(){
            validateNotEmpty.call(this);
            if($(this).val().toLowerCase() !== 'true' && $(this).val().toLowerCase() !== 'false'){
                $(this).parent().addClass('has-error');
                isValid = false;
                errorMessages.push(getVarName($(this)) + ' must be a boolean.')
            }
        };
        var validateListNumber = function validateListNumber(){
            var items, i;
            validateNotEmpty.call(this);
            if($(this).val().trim().endsWith(',')){
                $(this).parent().addClass('has-error');
                isValid = false;
            }else{
                items = $(this).val().split(',');
                for(i=0;i<items.length;i++){
                    if(!isNumber(items[i])){
                        $(this).parent().addClass('has-error');
                        isValid = false;
                        errorMessages.push(getVarName($(this)) + ' must be a comma seperated list of numbers.')
                        break;
                    }
                }
            }
        };
        var validateListText = function validateListText(){
            var items, i;
            validateNotEmpty.call(this);
            if($(this).val().trim().endsWith(',')){
                $(this).parent().addClass('has-error');
                isValid = false;
            }else{
                items = $(this).val().split(',');
                for(i=0;i<items.length;i++){
                    if(items[i].trim() === ''){
                        $(this).parent().addClass('has-error');
                        isValid = false;
                        errorMessages.push(getVarName($(this)) + ' must be a comma seperated list.')
                        break;
                    }
                }
            }
        };

        resetValidationStates();
        validateRunRange();
        $form.find('[data-type="text"]').each(validateText);
        $form.find('[data-type="number"]').each(validateNumber);
        $form.find('[data-type="boolean"]').each(validateBoolean);
        $form.find('[data-type="list_number"]').each(validateListNumber);
        $form.find('[data-type="list_text"]').each(validateListText);

        if(!isValid){
            $('.js-form-validation-message').html('');
            $('.js-form-validation-message').append($('<p/>').text('Please fix the following error:'));
            $errorList = $('<ul/>');
            for(var i=0;i<errorMessages.length;i++){
                $errorList.append($('<li/>').html(errorMessages[i]));
            }
            $('.js-form-validation-message').append($errorList).show();
        }

        return isValid;
    };

    var triggerAfterRunOptions = function triggerAfterRunOptions(){
        if($(this).val().trim() !== ''){
            $('#next_run').text(parseInt($(this).val())+1);
            $('#run_finish_warning').show();
        }else{
            $('#run_finish_warning').hide();
        }
    };

    var showDefaultSriptVariables = function showDefaultSriptVariables(){
        $('#default-variables-modal').modal();
    };

    var checkForConflicts = function checkForConflicts(successCallback){
        var start = parseInt($('#run_start').val());
        var end = parseInt($('#run_end').val());
        var conflicts = [];
        if($('#upcoming_runs').length > 0){
            var upcoming = $('#upcoming_runs').val().split(',');
            for(var i=0;i<upcoming.length;i++){
                if(parseInt(upcoming[i]) >= start && (!end || upcoming[i] <= end)){
                    conflicts.push(upcoming[i]);
                }
            }
        }
        if(conflicts.length === 0){
            successCallback();
        }else{
            $('.js-conflicts-list').text(conflicts.join(','));
            $('#conflicts-modal .js-conflicts-confirm').unbind('click').on('click', successCallback);
            $('#conflicts-modal').modal();
        }
    };

    var submitForm = function submitForm(event){
        var submitAction = function submitAction(){
            var $form = $('#run_variables');
            if($form.length===0) $form = $('#instrument_variables');
            $form.attr('action', formUrl);
            window.onbeforeunload = undefined;
            $form.submit();
        };
        var cancelAction = function cancelAction(){
            return false;
        };

        event.preventDefault();
        if(validateForm()){
            if($('#variable-range-toggle').length >0 && !$('#variable-range-toggle').bootstrapSwitch('state')){
                $('#variable-range-toggle-value').val('False');
                $('#run_start').val('');
                $('#run_end').val('');
                submitAction();
            }else{
                $('#variable-range-toggle-value').val('True');
                $('#experiment_reference').val('');
                checkForConflicts(submitAction);
            }
        }else{
            cancelAction();
        }
    };

    var restrictFinished = function restrictFinished(){
        var $end = $('#run_end');
        var $start = $('#run_start');
        var setMin = function setMin(){
            $end.attr('min', $start.val());
        };        
        $start.on('change', setMin);
        setMin();
    };

    var confirmUnsavedChanges = function confirmUnsavedChanges(){
        var $form = $('#run_variables');
        if($form.length===0) $form = $('#instrument_variables');

        $form.on('change', function(){
            $form.unbind('change');
            window.onbeforeunload = function confirmLeave(event) {
                if(!event) event = window.event;
                event.cancelBubble = true;
                event.returnValue = 'There are unsaved changes.';
                if (event.stopPropagation) {
                    event.stopPropagation();
                    event.preventDefault();
                }
            };

        });
    };

    var resetDefaultVariables = function resetDefaultVariables(event){
        event.preventDefault();
        var $form = $('#run_variables');
        if($form.length===0) $form = $('#instrument_variables');
        $form.find('.js-variables-container').html($('.js-default-variables').html());
        // We need to enable the popover again as the element is new
        $('[data-toggle="popover"]').popover();
    };

    var resetCurrentVariables = function resetCurrentVariables(event){
        event.preventDefault();
        var $form = $('#run_variables');
        if($form.length===0) $form = $('#instrument_variables');
        $form.find('.js-variables-container').html($('.js-current-variables').html());
        // We need to enable the popover again as the element is new
        $('[data-toggle="popover"]').popover();
    };

    var cancelForm = function cancelForm(event){
        event.preventDefault();
        window.onbeforeunload = undefined;
        window.location.href = document.referrer;
    };
    
    var toggleActionExplainations = function toggleActionExplainations(event){
        if(event.type==='mouseover'){
            $('.js-action-explaination').text($(this).siblings('.js-explaination').text());
        }else if(event.type==='mouseleave'){
            $('.js-action-explaination').text('');
        }
    };

    var updateBoolean = function updateBoolean(event){
        var isChecked = $(this).prop('checked');
        if(isChecked){
            isChecked = 'True';
        }else{
            isChecked = 'False';
        }
        $(this).val(isChecked).siblings('input[type=hidden]').val(isChecked);
    };

    var handleToggleSwitch = function handleToggleSwitch(){
        var toggleDisplay = function toggleDisplay(event, state){
            if(state){
                $('.js-variable-by-experiment').hide();
                $('.js-experiment-label').css('font-weight', 'normal').css('color', '#ccc');
                $('.js-variable-by-run').show();
                $('.js-run-label').css('font-weight', 'bold').css('color', '#000');
            }else{
                $('.js-variable-by-experiment').show();
                $('.js-experiment-label').css('font-weight', 'bold').css('color', '#000');
                $('.js-variable-by-run').hide();
                $('.js-run-label').css('font-weight', 'normal').css('color', '#ccc');
            }
        };

        $('.js-experiment-label,.js-run-label').css('cursor','default').css('font-weight', 'bold');
        toggleDisplay(undefined, $('#variable-range-toggle-value').val() === 'True');
        
        $('#variable-range-toggle').bootstrapSwitch();
        $('#variable-range-toggle').bootstrapSwitch('state', ($('#variable-range-toggle-value').val() === 'True'))
        $('#variable-range-toggle').on('switchChange.bootstrapSwitch', toggleDisplay);

        $('.js-experiment-label').on('click', function(){
            $('#variable-range-toggle').bootstrapSwitch('state', false);
        });

        $('.js-run-label').on('click', function(){
            $('#variable-range-toggle').bootstrapSwitch('state', true);
        });

    };

    var init = function init(){
        $('#run_variables,#instrument_variables').on('click', '#previewScript', previewScript);
        $('#script-preview-modal').on('click', '#downloadScript', downloadScript);
        $('#run_variables,#instrument_variables').on('click', '#resetValues', resetDefaultVariables);
        $('#run_variables,#instrument_variables').on('click', '#currentScript', resetCurrentVariables);
        $('#run_variables,#instrument_variables').on('click', '#variableSubmit', submitForm);
        $('#run_variables,#instrument_variables').on('click', '#cancelForm', cancelForm);
        $('#run_variables,#instrument_variables').on('click', 'input[type=checkbox][data-type=boolean]', updateBoolean);
        $('.js-form-actions li>a').on('mouseover mouseleave', toggleActionExplainations);
        $('#run_end').on('change', triggerAfterRunOptions);
        $('.js-show-default-variables').on('click', showDefaultSriptVariables);
        if($('#variable-range-toggle').length >0){
            handleToggleSwitch();
        }
        restrictFinished();
        confirmUnsavedChanges();
    };

    init();
}())